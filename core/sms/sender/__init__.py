from abc import ABC, abstractmethod

from core.logging.logger import logger


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
        pass

    @abstractmethod
    def send_sms(self, recipient: str, message: str):
        """
        Defines a method for sending an SMS.

        Args:
            recipient (str): The phone number or recipient of the SMS.
            message (str): The content of the SMS.
        """
        logger.debug(f"{recipient}: {message}")
        pass


class DebugSender(BaseSender):
    def __init__(self, *args, **kwargs):
        logger.debug('Debug Sender using')

    def send_sms(self, recipient: str, message: str):
        logger.info(f"{recipient}: {message}")

