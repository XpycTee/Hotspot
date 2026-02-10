
from core.config.response_code import NOT_AUTH, NOT_FOUND, OK, TIMEOUT
from core.logging import get_logger
from core.redis import cache


logger = get_logger('core.hotspot.auth.api.asterisk')

class AsteriskCallcheck():
    """

    """
    def add_phone(self, phone: str):
        phone_data = {
            'status': False,
        }
        cache.set(f'callcheck:asterisk:{phone}', phone_data, 300)
        logger.info('Phone was added successfully')

    def check_phone(self, phone: str):
        phone_data = cache.get(f'callcheck:asterisk:{phone}')
        if phone_data is None:
            logger.error('Callcheck tiomeout')
            return TIMEOUT
        
        check_status = phone_data.get('status')
        if not check_status:
            logger.error("Phone wasn't auth")
            return NOT_AUTH
        else:
            logger.info('Phone was auth successfully')
            return OK

    def confirm_phone(self, phone: str):
        phone_data = cache.get(f'callcheck:asterisk:{phone}')
        if phone_data is None:
            logger.error('Callcheck not found')
            return NOT_FOUND
        
        check_status = phone_data.get('status')
        if not check_status:
            phone_data['status'] = True
            cache.set(f'callcheck:asterisk:{phone}', phone_data, 300)
            return OK
