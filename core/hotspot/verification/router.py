from dataclasses import dataclass
from enum import Enum, auto
from core.config import get_config
from core.config.models.verificators import VProviderType, VerificationMethod, VerificationProvider
from core.hotspot.verification.api import ConfirmStatus, DeliveryStatus
from core.hotspot.verification.api.asterisk import AsteriskConfirm
from core.hotspot.verification.api.debug import DebugCallConfirmation, DebugCodeDelivery
from core.hotspot.verification.api.huawei import HuaweiSMSSender
from core.hotspot.verification.api.mikrotik import MikrotikSMSSender
from core.hotspot.verification.api.smsru import SMSRU


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
    call_phone:  str | None = None
    error_message: str | None = None


class VerificationRouter:
    def __init__(self):
        config = get_config()
        self._call_order = []
        self._code_order = []
        self._available_methods = set()

        call_order: list[VerificationProvider] = []
        code_order: list[VerificationProvider] = []
        for v in config.verificators.items:
            if v.enabled:
                self._available_methods.update(v.supported_methods)
                if VerificationMethod.CALL in v.supported_methods:
                    call_order.append(v)
                if VerificationMethod.CODE in v.supported_methods:
                    code_order.append(v)
                
        order = {value: index for index, value in enumerate(config.verificators.order)}
        self._call_order = sorted(call_order, key=lambda x: order[x.type])
        self._code_order = sorted(code_order, key=lambda x: order[x.type])

    @property
    def available_methods(self) -> set:
        return self._available_methods

    def send_code(self, recipient: str, code: str) -> VRouterResponse:
        last_error = "No code provider configured"
        for cfg in self._code_order:
            sender = None
            if cfg.type == VProviderType.SMSRU:
                sender = SMSRU(cfg.fields[0].value)
            elif cfg.type == VProviderType.MIKROTIK:
                sender = MikrotikSMSSender(cfg.fields[0].value)
            elif cfg.type == VProviderType.HUAWEI:
                sender = HuaweiSMSSender(cfg.fields[0].value)
            elif cfg.type == VProviderType.DEBUG:
                sender = DebugCodeDelivery()
            else:
                continue

            resp = sender.send_code(recipient, code)
            if resp.status == DeliveryStatus.SENT:
                return VRouterResponse(
                    status=VRouterStatus.SENDED,
                    provider=cfg.type,
                )
            
            if resp.status == DeliveryStatus.FAILED:
                last_error = resp.error_message or "Code delivery failed"

            if resp.status == DeliveryStatus.ERROR:
                last_error = resp.error_message or "Code delivery error"

        return VRouterResponse(
            status=VRouterStatus.ERROR,
            error_message=last_error,
        )


    def start_confirm(self, phone: str) -> VRouterResponse:
        last_error = "No call provider configured"
        for cfg in self._call_order:
            callcheck = None
            if cfg.type == VProviderType.SMSRU:
                callcheck = SMSRU(cfg.fields[0].value)
            elif cfg.type == VProviderType.ASTERISK:
                callcheck = AsteriskConfirm(cfg.fields[0].value)
            elif cfg.type == VProviderType.DEBUG:
                callcheck = DebugCallConfirmation()
            else:
                continue

            resp = callcheck.start_verification(phone)
            if resp.status == ConfirmStatus.PENDING:
                return VRouterResponse(
                    status=VRouterStatus.SENDED,
                    provider=cfg.type,
                    request_id=resp.request_id,
                    call_phone=resp.call_phone,
                )

            last_error = resp.error_message or "Call verification start failed"

        return VRouterResponse(
            status=VRouterStatus.ERROR,
            error_message=last_error,
        )


    def check_confirm(self, request_id: str, provider: VProviderType) -> VRouterResponse:
        callcheck = DebugCallConfirmation()
        selected_provider = provider
        for cfg in self._call_order:
            if cfg.type == provider:
                if provider == VProviderType.SMSRU:
                    callcheck = SMSRU(cfg.fields[0].value)
                    break
                elif provider == VProviderType.ASTERISK:
                    callcheck = AsteriskConfirm(cfg.fields[0].value)
                    break
                elif provider == VProviderType.DEBUG:
                    callcheck = DebugCallConfirmation()
                    break
        else:
            return VRouterResponse(
                status=VRouterStatus.ERROR,
                provider=selected_provider,
                error_message='Provider not configured',
            )

        resp = callcheck.check_verification(request_id)
        if resp.status == ConfirmStatus.VERIFIED:
            return VRouterResponse(
                status=VRouterStatus.VERIFIED,
                provider=selected_provider,
            )
        
        if resp.status == ConfirmStatus.PENDING:
            return VRouterResponse(
                status=VRouterStatus.SENDED,
                provider=selected_provider,
            )
        if resp.status == ConfirmStatus.TIEMOUT:
            return VRouterResponse(
                status=VRouterStatus.FAILED,
                provider=selected_provider,
                error_message='Timeout'
            )
        return VRouterResponse(
            status=VRouterStatus.ERROR,
            provider=selected_provider,
            error_message=resp.error_message or 'Call verification error',
        )
