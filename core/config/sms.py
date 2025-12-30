from core.config import get_config
from core.hotspot.sms.sender import BaseSender, DebugSender
from core.hotspot.sms.sender.huawei import HuaweiSMSSender
from core.hotspot.sms.sender.mikrotik import MikrotikSMSSender
from core.hotspot.sms.sender.smsru import SMSRUSender


def get_sender() -> BaseSender:
    config = get_config()

    senders = {
        'smsru': SMSRUSender,
        'mikrotik': MikrotikSMSSender,
        'huawei': HuaweiSMSSender,
        'debug': DebugSender
    }

    Sender = senders.get(config.sender.type, DebugSender)
    return Sender(**config.sender.params)
