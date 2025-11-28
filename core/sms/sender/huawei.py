from urllib.parse import urlparse

from huawei_lte_api.Client import Client
from huawei_lte_api.Connection import Connection
from huawei_lte_api.enums.client import ResponseEnum

from core.logging.logger import logger
from core.sms.sender import BaseSender


class HuaweiSMSSender(BaseSender):
    """
    HuaweiSMSSender class for sending SMS using Huawei SMS gateway.

    Args:
        url (str): The configuration URL for the Huawei SMS gateway API.

    Example:
        sender = HuaweiSMSSender('http://username:password@192.168.8.1/')
        sender.send_sms('+1234567890', 'Test message')
    """
    def __init__(self, url, *args, **kwargs):
        url_parsed = urlparse(url)
        is_correct = all([
                url_parsed.scheme,
                url_parsed.username,
                url_parsed.password,
                url_parsed.netloc,
                url_parsed.path])
        if not is_correct:
            raise AttributeError

        self._url = url

    def send_sms(self, recipient, message):
        with Connection(self._url) as connection:
            client = Client(connection)

            if client.sms.send_sms([recipient], message) == ResponseEnum.OK.value:
                logger.info('SMS was send successfully')
            else:
                logger.error('Error')
                return 1
