from environs import Env

from core.config import SETTINGS
from core.hotspot.sms.sender import BaseSender, DebugSender
from core.hotspot.sms.sender.huawei import HuaweiSMSSender
from core.hotspot.sms.sender.mikrotik import MikrotikSMSSender
from core.hotspot.sms.sender.smsru import SMSRUSender

env = Env(prefix='HOTSPOT_SENDER_')
env.read_env()


def get_sender() -> BaseSender:
    senders = {
        'smsru': SMSRUSender,
        'mikrotik': MikrotikSMSSender,
        'huawei': HuaweiSMSSender,
        'debug': DebugSender
    }
    sender_settings = SETTINGS.get('sender', {})
    sender_type = env.str('TYPE', sender_settings.get('type', 'debug'))
    Sender = senders.get(sender_type.lower(), DebugSender)

    with env.prefixed(f'{sender_type.upper()}_'):
        url = env.url('URL',sender_settings.get('url', None))
        apikey = env.str('APIKEY', sender_settings.get('api_key', None))

    sender_params = {}
    if url is not None:
        sender_params = {'url': url}
    elif apikey is not None:
        sender_params = {'api_key': apikey}

    return Sender(**sender_params)
