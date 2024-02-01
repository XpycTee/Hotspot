import logging

from huawei_lte_api.Client import Client
from huawei_lte_api.Connection import Connection
from huawei_lte_api.enums.client import ResponseEnum


class HuaweiSMSSender:
    """
    HuaweiSMSSender class for sending SMS using Huawei SMS gateway.

    Args:
        host (str): The hostname of the Huawei SMS gateway.
        username (str): The username for authentication.
        password (str): The password for authentication.
        port (str | int, optional): The port number for the connection. Defaults to None.
        https (bool, optional): Flag to indicate whether to use HTTPS. Defaults to False.

    Attributes:
        _url (str): The constructed URL for the Huawei SMS gateway API.

    Methods:
        sms_send(recipient: str, message: str): Sends an SMS to the specified recipient with the given message.

    Example:
        sender = HuaweiSMSSender('example.com', 'username', 'password')
        sender.sms_send('+1234567890', 'Test message')
    """
    def __init__(self, host: str, username: str, password: str, port: str | int = None, https: bool = False):
        scheme = 'https' if https else 'http'
        hostname = host
        port = str(443) if https else str(80) if not port else str(port)
        self._url = f"{scheme}://{username}:{password}@{hostname}:{port}/"

    def sms_send(self, recipient: str, message: str):
        with Connection(self._url) as connection:
            client = Client(connection)

            if client.sms.send_sms([recipient], message) == ResponseEnum.OK.value:
                logging.info('SMS was send successfully')
            else:
                logging.error('Error')
