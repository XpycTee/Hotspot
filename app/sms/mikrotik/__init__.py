import base64
import json
from urllib import request
from urllib import parse


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
    def __init__(self, host: str, user: str, password: str, port: str | int = None, https: bool = False):
        scheme = 'https' if https else 'http'
        hostname = host
        port = str(443) if https else str(80) if not port else str(port)
        self._path = '/rest/tool/sms'
        self._base64_auth = base64.b64encode(f'{user}:{password}'.encode('utf-8')).decode('utf-8')
        self._url = f"{scheme}://{hostname}:{port}"

    def _request(self, path=None, data=None):
        if path is None:
            path = self._path

        if not data:
            req = request.Request(self._url + path)
        else:
            encoded_data = parse.urlencode(data).encode()
            req = request.Request(self._url + path, data=encoded_data)
        req.add_header('Authorization', f'Basic {self._base64_auth}')
        res = request.urlopen(req)
        return json.loads(res.read())
