from abc import ABC, abstractmethod

from core.config.response_code import NOT_AUTH, OK
from core.logging import get_logger


logger = get_logger('core.hotspot.auth.api')

class BaseSender(ABC):
    """
    BaseSender class for sending code using different SMS gateways.

    Example:
        sender = BaseSender()
        sender.send_code('+1234567890', 1234)
    """
    @abstractmethod
    def __init__(self, *args, **kwargs):
        """
        Initializes the Sender with the provided connection parameters.
        """
        logger.debug((args, kwargs))

    @abstractmethod
    def send_code(self, recipient: str, code: str | int):
        """
        Defines a method for sending an code.

        Args:
            recipient (str): The phone number or recipient of the code.
            code (str): The code to be sent.
        """
        logger.debug(f"{recipient}: {code}")


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

    def send_code(self, recipient: str, message: str):
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
