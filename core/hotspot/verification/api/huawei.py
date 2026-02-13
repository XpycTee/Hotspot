from urllib.parse import urlparse

from huawei_lte_api.Client import Client
from huawei_lte_api.Connection import Connection
from huawei_lte_api.enums.client import ResponseEnum

from core.config.models.verificators import DeliveryStatus, SendCodeResult
from core.hotspot.verification.api import BaseSender
from core.logging import get_logger
from core.utils.language import get_translate


logger = get_logger('core.hotspot.verification.api.huawei')

class HuaweiSMSSender(BaseSender):
    """
    HuaweiSMSSender class for sending SMS using Huawei SMS gateway.

    Args:
        url (str): The configuration URL for the Huawei SMS gateway API.

    Example:
        sender = HuaweiSMSSender('http://username:password@192.168.8.1/')
        sender.send_code('+1234567890', 1234)
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

    def send_code(self, recipient, code):
        with Connection(self._url) as connection:
            client = Client(connection)
            message = get_translate('sms_code', templates={"code": code})
            if client.sms.send_sms([recipient], message) == ResponseEnum.OK.value:
                logger.info('SMS was send successfully')
                return SendCodeResult(
                    status=DeliveryStatus.SENT,
                )
            else:
                logger.error('Error')
                return SendCodeResult(
                    status=DeliveryStatus.ERROR,
                )
