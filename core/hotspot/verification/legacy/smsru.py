from smsru_api import Client

from core.config.response_code import ERROR, NOT_AUTH, NOT_FOUND, OK, TIMEOUT
from core.hotspot.verification.legacy import BaseCallcheck, BaseSender
from core.logging import get_logger
from core.redis import cache
from core.utils.language import get_translate


logger = get_logger('core.hotspot.verification.api.smsru')

class SMSRU(BaseSender, BaseCallcheck):
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
        provider.add_phone('+1234567890')

        # Check verification status from cache
        provider.check_phone('+1234567890')

        # Poll SmsRu API for verification status
        provider.check_polling('+1234567890')
    """
    def __init__(self, api_key, *args, **kwargs):
        self._api = Client(api_key)

    def send_code(self, recipient, code):
        message = get_translate('sms_code', templates={"code": code})
        resp = self._api.send(recipient, message=message)
        if resp.get('status') != "OK":
            logger.error('Error')
            return ERROR
        
        logger.info('SMS was send successfully')
        return OK
        
    def add_phone(self, phone: str):
        phone_data = self._api.callcheck_add(phone)
        if phone_data.get('status') != 'OK':
            logger.error('Error')
            return ERROR
        
        cache.set(f'callcheck:smsru:phone:{phone}', phone_data, 600)

        logger.info('Phone was added successfully')
        return OK

    def check_phone(self, phone: str):
        check_statuses = {
            400: False,
            401: True,
            402: TIMEOUT,
        }

        phone_data = cache.get(f'callcheck:smsru:phone:{phone}')
        check_id = phone_data.get('check_id')
        if check_id is None:
            logger.error('Callcheck not found')
            return NOT_FOUND

        check_data = cache.get(f'callcheck:smsru:id:{check_id}')
        if check_data is None:
            logger.error("Phone wasn't auth")
            return NOT_AUTH

        check_status = check_statuses.get(
            check_data.get('check_status')
        )

        if check_status == TIMEOUT:
            logger.error('Callcheck tiomeout')
            return TIMEOUT
        if check_status:
            logger.info('Phone was auth successfully')
            return OK
        logger.error("Phone wasn't auth")
        return NOT_AUTH

    def check_polling(self, phone: str):
        check_statuses = {
            400: False,
            401: True,
            402: TIMEOUT,
        }
        phone_data = cache.get(f'callcheck:smsru:phone:{phone}')
        check_id = phone_data.get('check_id')
        if check_id is None:
            logger.error('Callcheck not found')
            return NOT_FOUND

        check_data = self._api.callcheck_status(check_id)
        if check_data.get('status') != 'OK':
            logger.error('Error')
            return ERROR
        
        check_status = check_statuses.get(
            int(check_data.get('check_status'))
        )
        if check_status == TIMEOUT:
            logger.error('Callcheck tiomeout')
            return TIMEOUT
        if check_status:
            logger.info('Phone was auth successfully')
            return OK
        
        logger.error("Phone wasn't auth")
        return NOT_AUTH
