from smsru_api import Client

from core.config.response_code import ERROR, NOT_AUTH, NOT_FOUND, OK, TIMEOUT
from core.hotspot.auth.api import BaseSender
from core.logging import get_logger
from core.redis import cache


logger = get_logger('core.hotspot.auth.api.smsru')

class SMSRU(BaseSender):
    """
    SMSRUSender class for sending SMS using the SmsRu API.

    Args:
        api_key (str): The API key for accessing the SmsRu API.

    Example:
        sender = SMSRUSender('your_api_key')
        sender.send_sms('+1234567890', 'Test message')
    """
    def __init__(self, api_key, *args, **kwargs):
        self._api = Client(api_key)

    def send_sms(self, recipient, message):
        resp = self._api.send(recipient, message=message)
        if resp.get('status') != "OK":
            logger.error('Error')
            return ERROR
        
        logger.info('SMS was send successfully')
        return OK
        
    def add_phone(self, phone: str):
        resp = self._api.callcheck_add(phone)
        if resp.get('status') != 'OK':
            logger.error('Error')
            return ERROR
        
        check_id = resp.get('check_id')

        cache.set(f'callcheck:smsru:id:{phone}', check_id, 600)

        logger.info('Phone was added successfully')
        return OK

    def check_phone(self, phone: str):
        check_statuses = {
            400: False,
            401: True,
            402: TIMEOUT,
        }
        check_id = cache.get(f'callcheck:smsru:id:{phone}')
        if check_id is None:
            logger.error('Callcheck not found')
            return NOT_FOUND

        phone_data = cache.get(f'callcheck:smsru:{check_id}')
        if phone_data is None:
            logger.error("Phone wasn't auth")
            return NOT_AUTH

        check_status = check_statuses.get(phone_data.get('check_status'))

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
        check_id = cache.get(f'callcheck:smsru:id:{phone}')
        if check_id is None:
            logger.error('Callcheck not found')
            return NOT_FOUND

        resp = self._api.callcheck_status(check_id)
        if resp.get('status') != 'OK':
            logger.error('Error')
            return ERROR
        
        check_status = check_statuses.get(int(resp.get('check_status')))
        if check_status == TIMEOUT:
            logger.error('Callcheck tiomeout')
            return TIMEOUT
        if check_status:
            logger.info('Phone was auth successfully')
            return OK
        
        logger.error("Phone wasn't auth")
        return NOT_AUTH
