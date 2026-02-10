from core.config import get_config
from core.hotspot.auth.api import BaseSender, DebugSender
from core.hotspot.auth.api.huawei import HuaweiSMSSender
from core.hotspot.auth.api.mikrotik import MikrotikSMSSender
from core.hotspot.auth.api.smsru import SMSRUCallcheck, SMSRU


def get_sender() -> BaseSender:
    config = get_config()

    senders = {
        'smsru': SMSRU,
        'mikrotik': MikrotikSMSSender,
        'huawei': HuaweiSMSSender,
        'debug': DebugSender,
    }

    Sender = senders.get(config.sender.type, DebugSender)
    return Sender(**config.sender.params)

def get_callcheck() -> str:
    config = get_config()

    senders = {
        'smsru': SMSRU,
        'asterisk': 'AsteriskCallcheck',
        'debug': 'DebugCaller',
    }

    #Caller = senders.get(config.caller.type, 'DebugCaller')
    #return Caller(**config.caller.params)

    return 'DebugCaller'
