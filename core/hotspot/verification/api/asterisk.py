from uuid import uuid4
from core.hotspot.verification.api import CallConfirmationProvider, ConfirmResult, ConfirmStatus
from core.logging import get_logger
from core.redis import cache


logger = get_logger('core.hotspot.verification.api.asterisk')


class AsteriskConfirm(CallConfirmationProvider):
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

    def start_verification(self, phone: str):
        request_id = uuid4()
        phone_data = {
            'request_id': request_id,
            'status': False,
            'phone': phone,
        }
        cache.set(f'callcheck:asterisk:id:{request_id}', phone_data, 300)
        cache.set(f'callcheck:asterisk:phone:{phone}', request_id, 300)
        logger.info('Phone was added successfully')
        return ConfirmResult(
            status=ConfirmStatus.PENDING,
            request_id=request_id,
            call_phone=self._call_phone,
        )

    def check_verification(self, request_id: str):
        phone_data = cache.get(f'callcheck:asterisk:id:{request_id}')
        if phone_data is None:
            logger.error('Callcheck tiomeout')
            return ConfirmResult(
                status=ConfirmStatus.TIEMOUT,
            )
        
        check_status = phone_data.get('status')
        if not check_status:
            logger.error("Phone wasn't auth")
            return ConfirmResult(
                status=ConfirmStatus.PENDING,
            )
        else:
            logger.info('Phone was auth successfully')
            return ConfirmResult(
                status=ConfirmStatus.VERIFIED,
            )
