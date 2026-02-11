from core.config import get_config
from core.hotspot.auth.api import BaseSender, DebugSender
from core.hotspot.auth.api.asterisk import AsteriskCallcheck
from core.hotspot.auth.api.huawei import HuaweiSMSSender
from core.hotspot.auth.api.mikrotik import MikrotikSMSSender
from core.hotspot.auth.api.smsru import SMSRU


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

def get_callcheck() -> AsteriskCallcheck:
    config = get_config()

    callers = {
        'smsru': SMSRU,
        'asterisk': AsteriskCallcheck,
        'debug': 'DebugCaller',
    }
    return AsteriskCallcheck()

    Caller = callers.get('asterisk', 'DebugCaller')
    return Caller(**config.caller.params)
