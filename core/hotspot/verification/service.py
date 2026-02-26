from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum, auto
from random import randint
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
    def __init__(self, session_id: str):
        self._cache = RedisCache()
        chached_session = self._cache.get(f'verify:session:{session_id}')
        if chached_session is None:
            self._session = VerificationSession(
                session_id=session_id,
                status=VSessionStatus.START,
            )
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

    def _save_session(self):
        self._cache.set(f'verify:session:{self._session.session_id}', self._session, 600)

    def _clear_session(self):
        self._cache.delete(f'verify:session:{self._session.session_id}')

    def start_verification(self, phone: str) -> VerificationResponse:
        self._session.phone = phone
        self._save_session()

        router = VerificationRouter()
        methods = router.available_methods
        if not methods:
            raise NoAvailableMethodError()
        
        if VerificationMethod.CALL in methods:
            code_avail = (VerificationMethod.CODE in methods)

            router_resp = router.start_confirm(phone=self._session.phone)
            if router_resp.status == VRouterStatus.SENDED:
                self._session.status = VSessionStatus.WAIT_CALL
                self._session.call_id = router_resp.request_id
                self._session.provider = router_resp.provider
                self._session.timeout = (datetime.now() + timedelta(minutes=5))
                self._save_session()
                
                return VerificationResponse(
                    status=VerificationStatus.WAIT_CALL,
                    call_phone=router_resp.call_phone,
                    code_avail=code_avail,
                )

        if VerificationMethod.CODE in methods:
            return VerificationResponse(
                status=VerificationStatus.SENDING_CODE,
            )

        return VerificationResponse(
            status=VerificationStatus.ERROR,
            error_message=get_translate('errors.auth.bad_status'),
        )
        
    def send_code(self) -> VerificationResponse:
        if not self._session.phone:
            return VerificationResponse(
                status=VerificationStatus.FAILED,
                error_message=get_translate('errors.auth.bad_status'),
            )

        if self._session.status == VSessionStatus.WAIT_CODE:
            return VerificationResponse(
                status=VerificationStatus.FAILED,
                error_message=get_translate("errors.auth.code_can_not_resend"),
            )
        
        if self._session.code is None:
            self._session.code = str(randint(0, 9999)).zfill(4)
            self._session.attempts = 0
            self._session.timeout = (datetime.now() + timedelta(minutes=5))
            self._save_session()

        logger.debug(f"User's code for {self._session.phone}: {self._session.code}")

        router = VerificationRouter()
        router_resp = router.send_code(self._session.phone, self._session.code)

        if router_resp.status in (VRouterStatus.ERROR, VRouterStatus.FAILED):
            logger.error(f"Failed to send code to {self._session.phone}")
            return VerificationResponse(
                status=VerificationStatus.ERROR,
                error_message=router_resp.error_message,
            )
        
        if router_resp.status == VRouterStatus.SENDED:
            self._session.status = VSessionStatus.WAIT_CODE
            self._save_session()

            return VerificationResponse(
                status=VerificationStatus.WAIT_CODE,
            )

        return VerificationResponse(
            status=VerificationStatus.ERROR,
            error_message=get_translate('errors.auth.bad_status'),
        )
    
    def code_verification(self, code: str) -> VerificationResponse:
        if self._session.status != VSessionStatus.WAIT_CODE:
            return VerificationResponse(
                status=VerificationStatus.FAILED,
                error_message=get_translate('errors.auth.bad_status'),
            )

        if self._session.timeout and datetime.now() > self._session.timeout:
            self._clear_session()
            return VerificationResponse(
                status=VerificationStatus.FAILED,
                error_message=get_translate('errors.auth.expired_code'),
            )

        if self._session.code == code:
            self._clear_session()
            return VerificationResponse(
                status=VerificationStatus.VERIFIED,
            )

        self._session.attempts += 1
        self._save_session()

        if self._session.attempts < 3:
            return VerificationResponse(
                status=VerificationStatus.RETRY,
                error_message=get_translate('errors.auth.bad_code_try'),
            )

        self._clear_session()
        return VerificationResponse(
            status=VerificationStatus.DENIED,
            error_message=get_translate('errors.auth.bad_code_all'),
        )

    def call_verification(self) -> VerificationResponse:
        if self._session.status == VSessionStatus.WAIT_CALL:
            now_time = datetime.now()
            if self._session.timeout and now_time > self._session.timeout:
                self._clear_session()
                return VerificationResponse(
                    status=VerificationStatus.FAILED,
                    error_message=get_translate('errors.auth.timeout'),
                )

            router = VerificationRouter()
            router_resp = router.check_confirm(
                self._session.call_id,
                self._session.provider,
            )

            if router_resp.status == VRouterStatus.SENDED:
                return VerificationResponse(
                    status=VerificationStatus.WAIT_CALL,
                )
            if router_resp.status == VRouterStatus.ERROR:
                logger.error(f"Failed to verify call to {self._session.phone}")
                return VerificationResponse(
                    status=VerificationStatus.ERROR,
                    error_message=router_resp.error_message,
                )
            if router_resp.status == VRouterStatus.FAILED:
                return VerificationResponse(
                    status=VerificationStatus.FAILED,
                    error_message=router_resp.error_message,
                )
            if router_resp.status == VRouterStatus.VERIFIED:
                self._clear_session()
                return VerificationResponse(
                    status=VerificationStatus.VERIFIED,
                )

        return VerificationResponse(
            status=VerificationStatus.FAILED,
            error_message=get_translate('errors.auth.bad_status'),
        )
