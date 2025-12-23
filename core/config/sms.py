from core.config import get_config
from core.config.loader import ConfigLoader
from core.config.models import SenderConfig
from core.hotspot.sms.sender import BaseSender, DebugSender
from core.hotspot.sms.sender.huawei import HuaweiSMSSender
from core.hotspot.sms.sender.mikrotik import MikrotikSMSSender
from core.hotspot.sms.sender.smsru import SMSRUSender


def get_sender_config() -> SenderConfig:
    raw, version = get_config()
    data = ConfigLoader(raw, version).sender()
    return data


def get_sender() -> BaseSender:
    senders = {
        'smsru': SMSRUSender,
        'mikrotik': MikrotikSMSSender,
        'huawei': HuaweiSMSSender,
        'debug': DebugSender
    }
    sender_config = get_sender_config()

    Sender = senders.get(sender_config.type, DebugSender)
    return Sender(**sender_config.params)
