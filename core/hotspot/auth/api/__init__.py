from abc import ABC, abstractmethod

from core.config.response_code import NOT_AUTH, OK
from core.logging import get_logger


logger = get_logger('core.hotspot.sms.sender')

class BaseSender(ABC):
    """
    BaseSender class for sending SMS using different SMS gateways.

    Example:
        sender = BaseSender()
        sender.send_sms('+1234567890', 'Test message')
    """
    @abstractmethod
    def __init__(self, *args, **kwargs):
        """
        Initializes the Sender with the provided connection parameters.
        """
        logger.debug((args, kwargs))

    @abstractmethod
    def send_sms(self, recipient: str, message: str):
        """
        Defines a method for sending an SMS.

        Args:
            recipient (str): The phone number or recipient of the SMS.
            message (str): The content of the SMS.
        """
        logger.debug(f"{recipient}: {message}")


class BaseCallcheck(ABC):
    """
    BaseCallcheck class for managing phone verification via call-check providers.

    This abstract class defines the interface for services that:
    1. Register a phone number for verification.
    2. Check the verification status of a previously registered phone number.

    Example:
        callcheck = BaseCallcheck()
        callcheck.add_phone('+1234567890')
        callcheck.check_phone('+1234567890')
    """

    @abstractmethod
    def __init__(self, *args, **kwargs):
        """
        Initializes the Callcheck provider with the provided connection
        or authentication parameters.
        """
        logger.debug((args, kwargs))

    @abstractmethod
    def add_phone(self, phone: str) -> dict:
        """
        Registers a phone number in the call-check system.

        Args:
            phone (str): The phone number to be verified.
        """
        logger.debug(phone)

    @abstractmethod
    def check_phone(self, phone: str) -> dict:
        """
        Checks the verification status of a phone number.

        Args:
            phone (str): The phone number whose verification status
                         should be checked.
        """
        logger.debug(phone)
    

class DebugSender(BaseSender):
    def __init__(self, *args, **kwargs):
        logger.debug('Debug Sender using')

    def send_sms(self, recipient: str, message: str):
        logger.info(f"{recipient}: {message}")


class DebugCallcheck(BaseCallcheck):
    def __init__(self, *args, **kwargs):
        logger.debug('Debug Callcheck using')
        self._phones = {}

    def add_phone(self, phone: str):
        logger.info(f'Add phone: {phone}')
        self._phones[phone] = {'status': False, 'try': 0}
        return {'status': 'OK', 'call_phone': '1234567890'}

    def check_phone(self, phone: str):
        status = self._phones[phone].get('status')
        logger.info(f'Check phone {phone} status: {status}')
        self._phones[phone]['try'] += 1
        if self._phones[phone]['try'] > 10:
            return OK
        return NOT_AUTH
