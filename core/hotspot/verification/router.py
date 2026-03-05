from dataclasses import dataclass
from enum import Enum, auto
from typing import Any

from core.config import get_config
from core.config.models.verificators import VProviderType, VerificationMethod, VerificationProvider
from core.hotspot.verification.api import ConfirmStatus, DeliveryStatus
from core.hotspot.verification.api.asterisk import AsteriskConfirm
from core.hotspot.verification.api.debug import DebugCallConfirmation, DebugCodeDelivery
from core.hotspot.verification.api.huawei import HuaweiSMSSender
from core.hotspot.verification.api.mikrotik import MikrotikSMSSender
from core.hotspot.verification.api.smsru import SMSRU
from core.logging import get_logger

logger = get_logger('core.hotspot.verification.router')


class VRouterStatus(Enum):
    VERIFIED = auto()
    SENDED = auto()
    FAILED = auto()
    ERROR = auto()


@dataclass
class VRouterResponse:
    status: VRouterStatus
    provider: VProviderType | None = None

    # Options
    request_id: str | None = None
    call_phone: str | None = None
    error_message: str | None = None


class VerificationRouter:
    def __init__(self, flow_ctx: dict[str, Any] | None = None):
        self._flow_ctx = dict(flow_ctx or {})

        config = get_config()
        self._call_order = []
        self._code_order = []
        self._available_methods = set()

        call_order: list[VerificationProvider] = []
        code_order: list[VerificationProvider] = []
        for v in config.verificators.items:
            if v.enabled:
                supported_methods = {
                    method
                    for method in (
                        self._normalize_method(raw_method)
                        for raw_method in v.supported_methods
                    )
                    if method is not None
                }
                self._available_methods.update(supported_methods)
                if VerificationMethod.CALL in supported_methods:
                    call_order.append(v)
                if VerificationMethod.CODE in supported_methods:
                    code_order.append(v)

        order = {}
        for index, raw_provider in enumerate(config.verificators.order):
            normalized = self._normalize_provider(raw_provider)
            if normalized is not None:
                order[normalized] = index
        self._call_order = sorted(call_order, key=lambda x: order.get(self._normalize_provider(x.type), 999))
        self._code_order = sorted(code_order, key=lambda x: order.get(self._normalize_provider(x.type), 999))

    def _normalize_provider(self, raw_provider: Any) -> VProviderType | None:
        if isinstance(raw_provider, VProviderType):
            return raw_provider
        if isinstance(raw_provider, str):
            try:
                return VProviderType[raw_provider]
            except KeyError:
                try:
                    return VProviderType(raw_provider)
                except ValueError:
                    return None
        return None

    def _normalize_method(self, raw_method: Any) -> VerificationMethod | None:
        if isinstance(raw_method, VerificationMethod):
            return raw_method
        if isinstance(raw_method, str):
            try:
                return VerificationMethod[raw_method]
            except KeyError:
                try:
                    return VerificationMethod(raw_method)
                except ValueError:
                    return None
        return None

    def _provider_label(self, raw_provider: Any) -> str | None:
        normalized = self._normalize_provider(raw_provider)
        if normalized is not None:
            return normalized.name
        if raw_provider is None:
            return None
        return str(raw_provider)

    def _ctx(self, event: str, operation: str, **kwargs: Any) -> dict[str, Any]:
        ctx = dict(self._flow_ctx)
        ctx['event'] = event
        ctx['operation'] = operation
        for key, value in kwargs.items():
            if value is not None:
                ctx[key] = value
        return ctx

    def _prefix(self, ctx: dict[str, Any]) -> str:
        auth_flow = ctx.get('auth_flow_id') or '-'
        verify_flow = ctx.get('verify_session_id') or '-'
        stage = ctx.get('stage') or '-'
        return f'[auth_flow={auth_flow} verify={verify_flow} stage={stage}]'

    def _log(self, level: str, message: str, event: str, operation: str, **kwargs: Any):
        ctx = self._ctx(event, operation, **kwargs)
        log_fn = getattr(logger, level)
        log_fn(f'{self._prefix(ctx)} {message}', extra=ctx)

    @property
    def available_methods(self) -> set:
        return self._available_methods

    def send_code(self, recipient: str, code: str) -> VRouterResponse:
        last_error = "No code provider configured"
        last_provider = None
        self._log('debug', 'Starting code delivery routing', 'verify.code.send', 'send_code', providers=len(self._code_order))
        for cfg in self._code_order:
            provider_type = self._normalize_provider(cfg.type)
            sender = None
            if provider_type == VProviderType.SMSRU:
                sender = SMSRU(cfg.fields[0].value)
            elif provider_type == VProviderType.MIKROTIK:
                sender = MikrotikSMSSender(cfg.fields[0].value)
            elif provider_type == VProviderType.HUAWEI:
                sender = HuaweiSMSSender(cfg.fields[0].value)
            elif provider_type == VProviderType.DEBUG:
                sender = DebugCodeDelivery()
            else:
                continue

            self._log('debug', 'Trying code provider', 'verify.code.send', 'send_code', provider=self._provider_label(cfg.type))
            resp = sender.send_code(recipient, code)
            if resp.status == DeliveryStatus.SENT:
                self._log('info', 'Code provider accepted request', 'verify.code.send', 'send_code', provider=self._provider_label(cfg.type))
                return VRouterResponse(
                    status=VRouterStatus.SENDED,
                    provider=provider_type,
                )

            last_provider = provider_type or cfg.type
            if resp.status == DeliveryStatus.FAILED:
                last_error = resp.error_message or "Code delivery failed"
                self._log('warning', 'Code provider returned FAILED, fallback to next', 'verify.code.send', 'send_code', provider=self._provider_label(cfg.type), error_message=last_error)

            if resp.status == DeliveryStatus.ERROR:
                last_error = resp.error_message or "Code delivery error"
                self._log('warning', 'Code provider returned ERROR, fallback to next', 'verify.code.send', 'send_code', provider=self._provider_label(cfg.type), error_message=last_error)

        self._log('error', 'Code delivery providers exhausted', 'verify.code.send', 'send_code', provider=self._provider_label(last_provider), error_message=last_error)
        return VRouterResponse(
            status=VRouterStatus.ERROR,
            provider=last_provider,
            error_message=last_error,
        )

    def start_confirm(self, phone: str) -> VRouterResponse:
        last_error = "No call provider configured"
        last_provider = None
        self._log('debug', 'Starting call verification routing', 'verify.start', 'start_confirm', providers=len(self._call_order))
        for cfg in self._call_order:
            provider_type = self._normalize_provider(cfg.type)
            callcheck = None
            if provider_type == VProviderType.SMSRU:
                callcheck = SMSRU(cfg.fields[0].value)
            elif provider_type == VProviderType.ASTERISK:
                callcheck = AsteriskConfirm(cfg.fields[0].value)
            elif provider_type == VProviderType.DEBUG:
                callcheck = DebugCallConfirmation()
            else:
                continue

            self._log('debug', 'Trying call provider', 'verify.start', 'start_confirm', provider=self._provider_label(cfg.type))
            resp = callcheck.start_verification(phone)
            if resp.status == ConfirmStatus.PENDING:
                self._log('info', 'Call verification started by provider', 'verify.start', 'start_confirm', provider=self._provider_label(cfg.type), call_request_id=resp.request_id)
                return VRouterResponse(
                    status=VRouterStatus.SENDED,
                    provider=provider_type,
                    request_id=resp.request_id,
                    call_phone=resp.call_phone,
                )

            last_provider = provider_type or cfg.type
            last_error = resp.error_message or "Call verification start failed"
            self._log('warning', 'Call provider failed to start verification, fallback to next', 'verify.start', 'start_confirm', provider=self._provider_label(cfg.type), error_message=last_error)

        self._log('error', 'Call verification providers exhausted', 'verify.start', 'start_confirm', provider=self._provider_label(last_provider), error_message=last_error)
        return VRouterResponse(
            status=VRouterStatus.ERROR,
            provider=last_provider,
            error_message=last_error,
        )

    def check_confirm(self, request_id: str, provider: VProviderType) -> VRouterResponse:
        callcheck = DebugCallConfirmation()
        selected_provider = self._normalize_provider(provider) or provider
        selected_provider_enum = self._normalize_provider(provider)
        self._log('debug', 'Checking call verification status', 'verify.call.poll', 'check_confirm', provider=self._provider_label(selected_provider), call_request_id=request_id)
        for cfg in self._call_order:
            cfg_provider = self._normalize_provider(cfg.type)
            if cfg_provider == selected_provider_enum:
                if cfg_provider == VProviderType.SMSRU:
                    callcheck = SMSRU(cfg.fields[0].value)
                    break
                if cfg_provider == VProviderType.ASTERISK:
                    callcheck = AsteriskConfirm(cfg.fields[0].value)
                    break
                if cfg_provider == VProviderType.DEBUG:
                    callcheck = DebugCallConfirmation()
                    break
        else:
            self._log('error', 'Selected call provider is not configured', 'verify.call.poll', 'check_confirm', provider=self._provider_label(selected_provider))
            return VRouterResponse(
                status=VRouterStatus.ERROR,
                provider=selected_provider,
                error_message='Provider not configured',
            )

        resp = callcheck.check_verification(request_id)
        if resp.status == ConfirmStatus.VERIFIED:
            self._log('info', 'Call verification reported VERIFIED', 'verify.call.poll', 'check_confirm', provider=self._provider_label(selected_provider))
            return VRouterResponse(
                status=VRouterStatus.VERIFIED,
                provider=selected_provider,
            )

        if resp.status == ConfirmStatus.PENDING:
            self._log('debug', 'Call verification reported PENDING', 'verify.call.poll', 'check_confirm', provider=self._provider_label(selected_provider))
            return VRouterResponse(
                status=VRouterStatus.SENDED,
                provider=selected_provider,
            )
        if resp.status == ConfirmStatus.TIEMOUT:
            self._log('warning', 'Call verification reported TIMEOUT', 'verify.call.poll', 'check_confirm', provider=self._provider_label(selected_provider))
            return VRouterResponse(
                status=VRouterStatus.FAILED,
                provider=selected_provider,
                error_message='Timeout',
            )

        error_message = resp.error_message or 'Call verification error'
        self._log('error', 'Call verification reported ERROR', 'verify.call.poll', 'check_confirm', provider=self._provider_label(selected_provider), error_message=error_message)
        return VRouterResponse(
            status=VRouterStatus.ERROR,
            provider=selected_provider,
            error_message=error_message,
        )
