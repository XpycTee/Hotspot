from core.config import CONFIG
from core.hotspot.sms.sender import BaseSender, DebugSender
from core.hotspot.sms.sender.huawei import HuaweiSMSSender
from core.hotspot.sms.sender.mikrotik import MikrotikSMSSender
from core.hotspot.sms.sender.smsru import SMSRUSender


def get_sender() -> BaseSender:
    senders = {
        'smsru': SMSRUSender,
        'mikrotik': MikrotikSMSSender,
        'huawei': HuaweiSMSSender,
        'debug': DebugSender
    }

    Sender = senders.get(CONFIG.sender.type, DebugSender)
    return Sender(**CONFIG.sender.params)
