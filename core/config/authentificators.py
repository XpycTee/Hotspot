from core.config import get_config
from core.hotspot.auth.api import BaseCallcheck, BaseSender, DebugCallcheck, DebugSender
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

def get_callcheck() -> BaseCallcheck:
    config = get_config()

    callers = {
        'smsru': SMSRU,
        'asterisk': AsteriskCallcheck,
        'debug': DebugCallcheck,
    }

    Callcheck = callers.get(config.callcheck.type, DebugCallcheck)
    return Callcheck(**config.callcheck.params)
