import logging

from smsru_api import SmsRu

from ...sms import BaseSender


class SMSRUSender(BaseSender):
    """
    SMSRUSender class for sending SMS using the SmsRu API.

    Args:
        config (str): The API key for accessing the SmsRu API.

    Example:
        sender = SMSRUSender('your_api_key')
        sender.send_sms('+1234567890', 'Test message')
    """
    def __init__(self, config):
        self._api = SmsRu(config)

    def send_sms(self, recipient, message):
        if self._api.send(recipient, message=message).get('status') == "OK":
            logging.info('SMS was send successfully')
        else:
            logging.error('Error')
