import base64
import json
import logging

from urllib import request
from urllib import parse
from urllib import error


class MikrotikSMSSender:
    """
    A class for sending SMS using Mikrotik RouterOS API.

    Args:
        host (str): The hostname or IP address of the Mikrotik router.
        user (str): The username for authentication.
        password (str): The password for authentication.
        port (str | int, optional): The port number for the connection. Defaults to 443 for HTTPS and 80 for HTTP.
        https (bool, optional): Indicates whether to use HTTPS. Defaults to False.

    Methods:
        _request(self, path=None, data=None): Sends a request to the Mikrotik router with the specified path and data.

    Example:
        sender = MikrotikSMSSender('example.com', 'username', 'password')
        sender.sms_send('+1234567890', 'Test message')
    """
    def __init__(self, host: str, user: str, password: str, port: str | int = None, https: bool = False, interface: str = "lte1"):
        scheme = 'https' if https else 'http'
        hostname = host
        port = str(443) if https else str(80) if not port else str(port)
        self._path = '/rest/tool/sms/send'
        self._base64_auth = base64.b64encode(f'{user}:{password}'.encode('utf-8')).decode('utf-8')
        self._url = f"{scheme}://{hostname}:{port}"
        self._interface = interface

    def _request(self, data=None, path=None):
        path = path if path is not None else self._path
        req_url = self._url + path
        headers = {
            "Authorization": f"Basic {self._base64_auth}",
            "Content-type": "application/json"
        }
        req = request.Request(req_url, headers=headers)
        with request.urlopen(req, data=json.dumps(data).encode() if data else None) as res:
            return json.loads(res.read())

    def sms_send(self, recipient: str, message: str):
        data = {
            "phone-number": recipient,
            "message": message,
            "port": self._interface
        }
        try:
            return self._request(data=data)
        except error.HTTPError as e:
            if e.code == 500:
                res = json.loads(e.read())
                logging.error(res.get('detail'))
