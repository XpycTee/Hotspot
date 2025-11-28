from environs import Env

from core.sms.sender import DebugSender
from core.sms.sender.huawei import HuaweiSMSSender
from core.sms.sender.mikrotik import MikrotikSMSSender
from core.sms.sender.smsru import SMSRUSender

env = Env(prefix="HOTSPOT_SENDER_")
env.read_env()


def get_sender():
    senders = {
        "smsru": SMSRUSender,
        "mikrotik": MikrotikSMSSender,
        "huawei": HuaweiSMSSender,
        "debug": DebugSender
    }
    sender_type = env.str("TYPE")
    Sender = senders.get(sender_type.lower(), DebugSender)

    with env.prefixed(f'{sender_type}_'):
        url = env.url('URL', None)
        apikey = env.str("APIKEY", None)

    sender_params = {}
    if url is not None:
        sender_params = {"url": url}
    elif apikey is not None:
        sender_params = {"api_key": apikey}

    return Sender(**sender_params)
