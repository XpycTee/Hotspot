from abc import ABC, abstractmethod


class BaseSender(ABC):
    """
    BaseSender class for sending SMS using different SMS gateways.

    Example:
        sender = BaseSender('config')
        sender.send_sms('+1234567890', 'Test message')
    """
    @abstractmethod
    def __init__(self, config: str):
        """
        Initializes the Sender with the provided connection parameters.

        Args:
            config (str): The configuration parameter for initializing the sender.
        """
        pass

    @abstractmethod
    def send_sms(self, recipient: str, message: str):
        """
        Defines a method for sending an SMS.

        Args:
            recipient (str): The phone number or recipient of the SMS.
            message (str): The content of the SMS.
        """
        pass
