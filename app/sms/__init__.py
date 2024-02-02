from abc import ABC, abstractmethod


class BaseSender(ABC):
    """
    BaseSender class for sending SMS using different SMS gateways.

    Methods:
        __init__: Initializes the BaseSender with the provided connection parameters.
        send_sms: Sends an SMS to the specified recipient with the given message.

    Example:
        sender = BaseSender(params)
        sender.send_sms('+1234567890', 'Test message')
    """
    @abstractmethod
    def __init__(self, *args, **kwargs):
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
