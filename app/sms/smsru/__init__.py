import logging
from abc import ABC

from smsru_api import SmsRu

from ...sms import BaseSender


class SMSRUSender(BaseSender, ABC):
    """
    SMSRUSender class for sending SMS using the SmsRu API.

    Args:
        api_key (str): The API key for accessing the SmsRu API.

    Methods:
        __init__: Initializes the SMSRUSender with the provided API key.
        sms_send: Sends an SMS to the specified recipient with the given message.

    Example:
        sender = SMSRUSender('your_api_key')
        sender.sms_send('+1234567890', 'Test message')
    """
    def __init__(self, api_key: str):
        self._api = SmsRu(api_key)

    def sms_send(self, recipient, message):
        if self._api.send(recipient, message=message).get('status') == "OK":
            logging.info('SMS was send successfully')
        else:
            logging.error('Error')
