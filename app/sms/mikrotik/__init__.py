import base64
import json
import logging

from urllib import request
from urllib import error
from urllib.parse import urlparse

from ...sms import BaseSender


class MikrotikSMSSender(BaseSender):
    """
    A class for sending SMS using Mikrotik RouterOS API.

    Args:
        url (str): The URL for the Mikrotik router in the format 'http[s]://username:password@hostname[:port]/[?query]', where scheme is either 'http' or 'https', username and password are for authentication, hostname is the IP address or hostname of the Mikrotik router, port is the port number for the connection, path is the API path, and query is the optional interface parameter.

    Example:
        sender = MikrotikSMSSender('https://username:password@192.168.88.1/[?interface=lte1]')
        sender.send_sms('+1234567890', 'Test message')
    """
    def __init__(self, url, *args, **kwargs):
        url_parsed = urlparse(url)

        if not all([url_parsed.scheme, url_parsed.username, url_parsed.password, url_parsed.netloc, url_parsed.path]):
            raise AttributeError

        self._interface = url_parsed.query.split('=')[1] if url_parsed.query else "lte1"

        username = url_parsed.username
        password = url_parsed.password
        scheme = url_parsed.scheme
        hostname = url_parsed.hostname
        port = str(443) if scheme == 'https' else str(80) if not url_parsed.port else str(url_parsed.port)

        self._path = '/rest/tool/sms/send'
        self._base64_auth = base64.b64encode(f'{username}:{password}'.encode('utf-8')).decode('utf-8')
        self._url = f"{scheme}://{hostname}:{port}"

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

    def send_sms(self, recipient, message):
        data = {
            "phone-number": recipient,
            "message": message,
            "port": self._interface
        }
        try:
            return self._request(data=data)
        except error.HTTPError as e:
            res = json.loads(e.read())
            logging.error(res.get('detail'))
            return res
