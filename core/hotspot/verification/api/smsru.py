from enum import Enum
from smsru_api import Client

from core.hotspot.verification.api import CallConfirmationProvider, CodeDeliveryProvider, ConfirmResult, ConfirmStatus, DeliveryStatus, SendCodeResult
from core.logging import get_logger
from core.redis import cache
from core.utils.language import get_translate


logger = get_logger('core.hotspot.verification.api.smsru')


SMSRU_STATUS = {
    400: ConfirmStatus.PENDING,
    401: ConfirmStatus.VERIFIED,
    402: ConfirmStatus.TIEMOUT,
}


class SMSRU(CodeDeliveryProvider, CallConfirmationProvider):
    """
    SMSRU provider implementation for the SmsRu API.

    This class implements both:
        • SMS sending functionality (BaseSender)
        • Phone verification via call-check mechanism (BaseCallcheck)

    Supported features:
        1. Sending SMS messages.
        2. Registering a phone number for call-check verification.
        3. Checking verification status from cache.
        4. Polling SmsRu API for real-time call-check status.

    Args:
        api_key (str): API key for authenticating with the SmsRu service.

    Example:
        provider = SMSRU('your_api_key')

        # Send SMS
        provider.send_code('+1234567890', 1234)

        # Start call-check verification
        provider.start_verification('+1234567890')

        # Check verification status from cache
        provider.check_verification('request_id')

        # Poll SmsRu API for verification status
        provider.check_polling('request_id')
    """
    def __init__(self, api_key, *args, **kwargs):
        self._api = Client(api_key)

    def send_code(self, recipient, code):
        message = get_translate('sms_code', templates={"code": code})
        resp = self._api.send(recipient, message=message, test=True)
        if resp.get('status') != "OK":
            if 104 <= resp.get('status_code') <= 150:
                return SendCodeResult(
                    status=DeliveryStatus.FAILED,
                    error_message=resp.get('status_text'),
                )
            logger.error(f'Error: {resp}')
            return SendCodeResult(
                status=DeliveryStatus.ERROR,
                error_message=resp.get('status_text'),
            )
        
        logger.info('Code was send successfully')
        return SendCodeResult(
                status=DeliveryStatus.SENT,
            )
        
    def start_verification(self, phone):
        phone_data = self._api.callcheck_add(phone)
        if phone_data.get('status') != 'OK':
            logger.error('Error')
            status_text = phone_data.get('status_text')
            return ConfirmResult(
                status=ConfirmStatus.ERROR,
                error_message=status_text,
            )
        
        check_id = phone_data.get('check_id')
        
        # call_phone = phone_data.get('call_phone')      # Format: 7XXXXXXXXXX
        call_phone = phone_data.get('call_phone_pretty') # Format: +7 (XXX) XXX-XXXX

        cache_data = {
            'start': phone_data,
            'confirm': {
                'check_status': 400,
            },
        }
        cache.set(f'callcheck:smsru:id:{check_id}', cache_data, 600)
        
        return ConfirmResult(
            status=ConfirmStatus.PENDING,
            request_id=check_id,
            call_phone=call_phone,
        )

    def check_verification(self, request_id):
        phone_data: dict = cache.get(f'callcheck:smsru:id:{request_id}')
        confirm_data: dict = phone_data.get('confirm')
        check_status = confirm_data.get('check_status')
        return ConfirmResult(
            status=SMSRU_STATUS[check_status],
        )

    def check_polling(self, request_id: str) -> ConfirmResult:
        check_data = self._api.callcheck_status(request_id)
        check_status = int(check_data.get('check_status'))
        if check_data.get('status') != 'OK':
            status_text = check_data.get('status_text')
            logger.error(f'Not OK status: {status_text}')
            return ConfirmResult(
                status=ConfirmStatus.ERROR,
                error_message=status_text,
            )

        return ConfirmResult(
            status=SMSRU_STATUS[check_status]
        )
