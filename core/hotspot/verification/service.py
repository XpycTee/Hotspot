from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum, auto
from random import randint
from typing import Any

from core.config.models.verificators import VerificationMethod
from core.exceptions.verification import NoAvailableMethodError
from core.hotspot.verification.router import VRouterStatus, VerificationRouter
from core.logging import get_logger
from core.redis.cache import RedisCache
from core.utils.language import get_translate

logger = get_logger('core.hotspot.verification.service')


class VerificationStatus(Enum):
    WAIT_CALL = auto()
    SENDING_CODE = auto()
    WAIT_CODE = auto()
    VERIFIED = auto()
    FAILED = auto()
    RETRY = auto()
    TIMEOUT = auto()
    ERROR = auto()
    DENIED = auto()


class VSessionStatus(Enum):
    START = auto()
    WAIT_CALL = auto()
    WAIT_CODE = auto()
    VERIFIED = auto()
    FAILED = auto()
    TIMEOUT = auto()
    ERROR = auto()


@dataclass
class VerificationResponse:
    status: VerificationStatus

    # Options
    call_phone: str | None = None
    code_avail: bool = False
    error_message: str | None = None


@dataclass
class VerificationSession:
    session_id: str
    status: VSessionStatus
    phone: str | None = None

    # Options
    provider: str | None = None

    # Call
    call_id: str | None = None

    # Code
    code: str | None = None
    attempts: int = 0
    timeout: datetime | None = None


class Verification:
    def __init__(self, session_id: str, flow_ctx: dict[str, Any] | None = None):
        self._cache = RedisCache()
        self._flow_ctx = dict(flow_ctx or {})
        self._flow_ctx['verify_session_id'] = session_id

        chached_session = self._cache.get(f'verify:session:{session_id}')
        if chached_session is None:
            self._session = VerificationSession(
                session_id=session_id,
                status=VSessionStatus.START,
            )
            self._log('debug', 'Initialized new verification session', 'verify.start', session_status=self._session.status.name)
        else:
            cached_status = chached_session.get('status')
            try:
                if isinstance(cached_status, int):
                    chached_session['status'] = VSessionStatus(cached_status)
                elif isinstance(cached_status, str):
                    if cached_status.isdigit():
                        chached_session['status'] = VSessionStatus(int(cached_status))
                    else:
                        chached_session['status'] = VSessionStatus[cached_status]
            except (ValueError, KeyError):
                chached_session['status'] = VSessionStatus.START
            self._session = VerificationSession(**chached_session)
            self._log('debug', 'Loaded verification session from cache', 'verify.start', session_status=self._session.status.name)

    def _mask_phone(self, phone: str | None) -> str | None:
        if not phone:
            return None
        if len(phone) <= 4:
            return '*' * len(phone)
        return '*' * (len(phone) - 4) + phone[-4:]

    def _ctx(self, event: str, **kwargs: Any) -> dict[str, Any]:
        ctx = dict(self._flow_ctx)
        ctx['event'] = event
        for key, value in kwargs.items():
            if value is not None:
                ctx[key] = value
        return ctx

    def _name_or_value(self, raw_value: Any) -> str | None:
        if raw_value is None:
            return None
        return getattr(raw_value, 'name', str(raw_value))

    def _prefix(self, ctx: dict[str, Any]) -> str:
        auth_flow = ctx.get('auth_flow_id') or '-'
        verify_flow = ctx.get('verify_session_id') or '-'
        stage = ctx.get('stage') or '-'
        return f'[auth_flow={auth_flow} verify={verify_flow} stage={stage}]'

    def _log(self, level: str, message: str, event: str, **kwargs: Any):
        ctx = self._ctx(event, **kwargs)
        log_fn = getattr(logger, level)
        log_fn(f'{self._prefix(ctx)} {message}', extra=ctx)

    def _save_session(self):
        self._cache.set(f'verify:session:{self._session.session_id}', self._session, 600)

    def _clear_session(self):
        self._cache.delete(f'verify:session:{self._session.session_id}')

    def start_verification(self, phone: str) -> VerificationResponse:
        self._session.phone = phone
        self._save_session()

        router = VerificationRouter(flow_ctx=self._ctx('verify.start'))
        methods = router.available_methods
        self._log(
            'debug',
            'Verification methods evaluated',
            'verify.start',
            available_methods=[self._name_or_value(m) for m in methods],
            phone=self._mask_phone(phone),
        )
        if not methods:
            self._log('error', 'No verification methods available', 'verify.start')
            raise NoAvailableMethodError()

        if VerificationMethod.CALL in methods:
            code_avail = VerificationMethod.CODE in methods

            router_resp = router.start_confirm(phone=self._session.phone)
            if router_resp.status == VRouterStatus.SENDED:
                self._session.status = VSessionStatus.WAIT_CALL
                self._session.call_id = router_resp.request_id
                self._session.provider = router_resp.provider
                self._session.timeout = datetime.now() + timedelta(minutes=5)
                self._save_session()
                self._log(
                    'info',
                    'Call verification started',
                    'verify.start',
                    session_status=self._session.status.name,
                    provider=self._name_or_value(router_resp.provider),
                    call_request_id=router_resp.request_id,
                    code_avail=code_avail,
                )

                return VerificationResponse(
                    status=VerificationStatus.WAIT_CALL,
                    call_phone=router_resp.call_phone,
                    code_avail=code_avail,
                )

            self._log(
                'warning',
                'Call verification provider did not start flow, trying fallback method',
                'verify.start',
                router_status=router_resp.status.name,
                error_message=router_resp.error_message,
            )

        if VerificationMethod.CODE in methods:
            self._log('info', 'Falling back to code verification flow', 'verify.start')
            return VerificationResponse(
                status=VerificationStatus.SENDING_CODE,
            )

        self._log('error', 'Verification flow ended in bad status', 'verify.start')
        return VerificationResponse(
            status=VerificationStatus.ERROR,
            error_message=get_translate('errors.hotspot.verify.bad_status'),
        )

    def send_code(self) -> VerificationResponse:
        if not self._session.phone:
            self._log('warning', 'Cannot send code without phone in verification session', 'verify.code.send')
            return VerificationResponse(
                status=VerificationStatus.FAILED,
                error_message=get_translate('errors.hotspot.verify.bad_status'),
            )

        if self._session.status == VSessionStatus.WAIT_CODE:
            self._log('warning', 'Code resend denied due to WAIT_CODE state', 'verify.code.send', session_status=self._session.status.name)
            return VerificationResponse(
                status=VerificationStatus.FAILED,
                error_message=get_translate("errors.hotspot.verify.code_can_not_resend"),
            )

        if self._session.code is None:
            self._session.code = str(randint(0, 9999)).zfill(4)
            self._session.attempts = 0
            self._session.timeout = datetime.now() + timedelta(minutes=5)
            self._save_session()
            self._log('debug', 'Verification code generated', 'verify.code.send', code_generated=True)

        router = VerificationRouter(flow_ctx=self._ctx('verify.code.send'))
        router_resp = router.send_code(self._session.phone, self._session.code)

        if router_resp.status in (VRouterStatus.ERROR, VRouterStatus.FAILED):
            self._log(
                'error',
                'Failed to send verification code via providers',
                'verify.code.send',
                router_status=router_resp.status.name,
                error_message=router_resp.error_message,
                phone=self._mask_phone(self._session.phone),
            )
            return VerificationResponse(
                status=VerificationStatus.ERROR,
                error_message=router_resp.error_message,
            )

        if router_resp.status == VRouterStatus.SENDED:
            self._session.status = VSessionStatus.WAIT_CODE
            self._save_session()
            self._log('info', 'Verification code sent successfully', 'verify.code.send', session_status=self._session.status.name)

            return VerificationResponse(
                status=VerificationStatus.WAIT_CODE,
            )

        self._log('error', 'Code sending ended in bad router status', 'verify.code.send', router_status=router_resp.status.name)
        return VerificationResponse(
            status=VerificationStatus.ERROR,
            error_message=get_translate('errors.hotspot.verify.bad_status'),
        )

    def code_verification(self, code: str) -> VerificationResponse:
        if self._session.status != VSessionStatus.WAIT_CODE:
            self._log('warning', 'Code verification requested in invalid state', 'verify.code.check', session_status=self._session.status.name)
            return VerificationResponse(
                status=VerificationStatus.FAILED,
                error_message=get_translate('errors.hotspot.verify.bad_status'),
            )

        if self._session.timeout and datetime.now() > self._session.timeout:
            self._clear_session()
            self._log('warning', 'Code verification timeout reached', 'verify.code.check')
            return VerificationResponse(
                status=VerificationStatus.FAILED,
                error_message=get_translate('errors.hotspot.verify.expired_code'),
            )

        if self._session.code == code:
            self._clear_session()
            self._log('info', 'Code verification passed', 'verify.code.check')
            return VerificationResponse(
                status=VerificationStatus.VERIFIED,
            )

        self._session.attempts += 1
        self._save_session()

        if self._session.attempts < 3:
            self._log('warning', 'Code verification retry required', 'verify.code.check', attempts=self._session.attempts)
            return VerificationResponse(
                status=VerificationStatus.RETRY,
                error_message=get_translate('errors.hotspot.verify.bad_code_try'),
            )

        self._clear_session()
        self._log('warning', 'Code verification denied due to attempts limit', 'verify.code.check', attempts=self._session.attempts)
        return VerificationResponse(
            status=VerificationStatus.DENIED,
            error_message=get_translate('errors.hotspot.verify.bad_code_all'),
        )

    def call_verification(self) -> VerificationResponse:
        if self._session.status == VSessionStatus.WAIT_CALL:
            now_time = datetime.now()
            if self._session.timeout and now_time > self._session.timeout:
                self._clear_session()
                self._log('warning', 'Call verification timeout reached', 'verify.call.poll')
                return VerificationResponse(
                    status=VerificationStatus.TIMEOUT,
                    error_message=get_translate('errors.hotspot.verify.timeout'),
                )

            router = VerificationRouter(flow_ctx=self._ctx('verify.call.poll'))
            router_resp = router.check_confirm(
                self._session.call_id,
                self._session.provider,
            )

            if router_resp.status == VRouterStatus.SENDED:
                self._log('debug', 'Call verification still pending', 'verify.call.poll', router_status=router_resp.status.name)
                return VerificationResponse(
                    status=VerificationStatus.WAIT_CALL,
                )
            if router_resp.status == VRouterStatus.ERROR:
                self._log(
                    'error',
                    'Call verification failed due to provider error',
                    'verify.call.poll',
                    router_status=router_resp.status.name,
                    error_message=router_resp.error_message,
                    phone=self._mask_phone(self._session.phone),
                )
                return VerificationResponse(
                    status=VerificationStatus.ERROR,
                    error_message=router_resp.error_message,
                )
            if router_resp.status == VRouterStatus.FAILED:
                self._log(
                    'warning',
                    'Call verification failed',
                    'verify.call.poll',
                    router_status=router_resp.status.name,
                    error_message=router_resp.error_message,
                )
                return VerificationResponse(
                    status=VerificationStatus.FAILED,
                    error_message=router_resp.error_message,
                )
            if router_resp.status == VRouterStatus.VERIFIED:
                self._clear_session()
                self._log('info', 'Call verification passed', 'verify.call.poll')
                return VerificationResponse(
                    status=VerificationStatus.VERIFIED,
                )

        self._log('warning', 'Call verification requested in invalid state', 'verify.call.poll', session_status=self._session.status.name)
        return VerificationResponse(
            status=VerificationStatus.FAILED,
            error_message=get_translate('errors.hotspot.verify.bad_status'),
        )
