
from core.config.response_code import NOT_AUTH, OK, TIMEOUT
from core.hotspot.verification.legacy import BaseCallcheck
from core.logging import get_logger
from core.redis import cache


logger = get_logger('core.hotspot.verification.api.asterisk')

class AsteriskCallcheck(BaseCallcheck):
    """
    AsteriskCallcheck implementation for phone verification using an Asterisk PBX system.

    This provider implements only call-check functionality and does not support SMS sending.

    The verification flow is based on:
        1. Registering a phone number in cache with an initial unauthenticated status.
        2. Expecting an external Asterisk event (e.g., AGI/webhook/AMI handler)
           to update the cached verification status.
        3. Checking the cached status to determine whether the phone has been verified.

    Verification data is stored in cache with a short TTL.

    Args:
        call_phone (str): The phone number that the user must call (or
                          from which an incoming call is expected) in order
                          to complete verification.

    Example:
        provider = AsteriskCallcheck(call_phone='+1000000000')

        # Register phone for verification
        provider.add_phone('+1234567890')

        # Later, after Asterisk updates verification status
        provider.check_phone('+1234567890')
    """

    def __init__(self, call_phone: str):
        self._call_phone = call_phone

    def add_phone(self, phone: str):
        phone_data = {
            'status': False,
        }
        cache.set(f'callcheck:asterisk:{phone}', phone_data, 300)
        logger.info('Phone was added successfully')
        return {'status': 'OK', 'call_phone': self._call_phone}

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
