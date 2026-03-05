from smsru_api import Client

from core.hotspot.verification.api import (
    CallConfirmationProvider,
    CodeDeliveryProvider,
    ConfirmResult,
    ConfirmStatus,
    DeliveryStatus,
    SendCodeResult,
)
from core.logging import get_logger
from core.redis import get_cache
from core.utils.language import get_translate

logger = get_logger('core.hotspot.verification.api.smsru')


SMSRU_STATUS = {
    400: ConfirmStatus.PENDING,
    401: ConfirmStatus.VERIFIED,
    402: ConfirmStatus.TIEMOUT,
}
CALLCHECK_CACHE_TTL_SECONDS = 600


class SMSRU(CodeDeliveryProvider, CallConfirmationProvider):
    def __init__(self, api_key, *args, **kwargs):
        self._api = Client(api_key)

    def _mask_phone(self, phone: str | None) -> str | None:
        if not phone:
            return None
        if len(phone) <= 4:
            return '*' * len(phone)
        return '*' * (len(phone) - 4) + phone[-4:]

    def _log(self, level: str, message: str, **extra):
        log_fn = getattr(logger, level)
        log_fn(message, extra=extra)

    def send_code(self, recipient, code):
        message = get_translate('sms_code', templates={"code": code})
        resp = self._api.send(recipient, message=message)
        status = resp.get('status')
        status_code = resp.get('status_code')
        if status != "OK":
            status_text = resp.get('status_text')
            if isinstance(status_code, int) and 104 <= status_code <= 150:
                self._log(
                    'warning',
                    'smsru send_code rejected by provider',
                    event='verify.provider.smsru.send_code',
                    error_kind='provider_reject',
                    recipient=self._mask_phone(recipient),
                    status=status,
                    status_code=status_code,
                )
                return SendCodeResult(
                    status=DeliveryStatus.FAILED,
                    error_message=status_text,
                )
            self._log(
                'error',
                'smsru send_code provider error',
                event='verify.provider.smsru.send_code',
                error_kind='provider_error',
                recipient=self._mask_phone(recipient),
                status=status,
                status_code=status_code,
            )
            return SendCodeResult(
                status=DeliveryStatus.ERROR,
                error_message=status_text,
            )

        self._log(
            'info',
            'smsru send_code accepted',
            event='verify.provider.smsru.send_code',
            recipient=self._mask_phone(recipient),
            status=status,
            status_code=status_code,
        )
        return SendCodeResult(
            status=DeliveryStatus.SENT,
        )

    def start_verification(self, phone):
        phone_data = self._api.callcheck_add(phone)
        status = phone_data.get('status')
        if status != 'OK':
            status_text = phone_data.get('status_text')
            self._log(
                'error',
                'smsru start_verification failed',
                event='verify.provider.smsru.start',
                error_kind='provider_error',
                phone=self._mask_phone(phone),
                status=status,
            )
            return ConfirmResult(
                status=ConfirmStatus.ERROR,
                error_message=status_text,
            )

        check_id = phone_data.get('check_id')

        # call_phone = phone_data.get('call_phone')      # Format: 7XXXXXXXXXX
        call_phone = phone_data.get('call_phone_pretty')  # Format: 8 (XXX) XXX-XXXX

        cache_data = {
            'start': phone_data,
            'confirm': {
                'check_status': 400,
            },
        }
        with get_cache() as cache:
            cache.set(f'callcheck:smsru:id:{check_id}', cache_data, CALLCHECK_CACHE_TTL_SECONDS)
            cache.set(f'callcheck:smsru:counter:{check_id}', 0, CALLCHECK_CACHE_TTL_SECONDS)

        self._log(
            'info',
            'smsru start_verification accepted',
            event='verify.provider.smsru.start',
            phone=self._mask_phone(phone),
            request_id=check_id,
            status=status,
        )
        return ConfirmResult(
            status=ConfirmStatus.PENDING,
            request_id=check_id,
            call_phone=call_phone,
        )

    def check_verification(self, request_id):
        id_key = f'callcheck:smsru:id:{request_id}'
        counter_key = f'callcheck:smsru:counter:{request_id}'

        with get_cache() as cache:
            phone_data: dict | None = cache.get(id_key)
            if phone_data is None:
                self._log(
                    'error',
                    'smsru check_verification timeout',
                    event='verify.provider.smsru.check',
                    error_kind='timeout',
                    request_id=request_id,
                )
                return ConfirmResult(
                    status=ConfirmStatus.TIEMOUT,
                )

            check_counter = cache.incr(counter_key)

            if check_counter % 3 == 0:
                return self.check_polling(request_id)

        confirm_data: dict = phone_data.get('confirm')
        check_status = confirm_data.get('check_status')

        ret_status = SMSRU_STATUS[check_status]
        self._log(
            'debug',
            'smsru check_verification cache status',
            event='verify.provider.smsru.check',
            request_id=request_id,
            check_status=check_status,
            status=ret_status.name,
        )
        return ConfirmResult(
            status=ret_status,
        )

    def check_polling(self, request_id: str) -> ConfirmResult:
        try:
            check_data = self._api.callcheck_status(request_id)
        except Exception as exc:
            self._log(
                'warning',
                'smsru polling temporary failure',
                event='verify.provider.smsru.poll',
                error_kind='provider_error',
                request_id=request_id,
                error_type=type(exc).__name__,
            )
            # Temporary provider/network failures should not break verification flow.
            return ConfirmResult(
                status=ConfirmStatus.PENDING,
            )

        status = check_data.get('status')
        if status != 'OK':
            status_text = check_data.get('status_text')
            self._log(
                'error',
                'smsru polling returned non-OK status',
                event='verify.provider.smsru.poll',
                error_kind='provider_error',
                request_id=request_id,
                status=status,
            )
            return ConfirmResult(
                status=ConfirmStatus.ERROR,
                error_message=status_text,
            )

        try:
            check_status = int(check_data.get('check_status'))
        except (TypeError, ValueError):
            self._log(
                'error',
                'smsru polling returned invalid check_status',
                event='verify.provider.smsru.poll',
                error_kind='invalid_response',
                request_id=request_id,
            )
            return ConfirmResult(
                status=ConfirmStatus.ERROR,
                error_message='Invalid provider response',
            )

        mapped_status = SMSRU_STATUS.get(check_status, ConfirmStatus.ERROR)
        self._log(
            'debug',
            'smsru polling status mapped',
            event='verify.provider.smsru.poll',
            request_id=request_id,
            check_status=check_status,
            status=mapped_status.name,
        )
        return ConfirmResult(
            status=mapped_status,
        )
