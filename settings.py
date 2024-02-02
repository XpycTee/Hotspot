import os

from app.sms.huawei import HuaweiSMSSender
from app.sms.mikrotik import MikrotikSMSSender
from app.sms.smsru import SMSRUSender

basedir = os.path.abspath(os.path.dirname(__file__))


class Config:
    _default_sql_url = 'sqlite:///' + os.path.join(basedir, 'app/database/hotspot.db')

    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URI') or _default_sql_url
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    key = [key for key in os.environ.keys() if key.endswith('_SENDER_CFG')][0]
    sender_name = key.split('_')[0]
    sender_config = os.environ.get(key)
    senders = {
        "SMSRU": SMSRUSender,
        "MIKROTIK": MikrotikSMSSender,
        "HUAWEI": HuaweiSMSSender,
    }
    sender = senders.get(sender_name)
    SENDER = sender(sender_config)

    HOTSPOT_USER = os.environ.get('HOTSPOT_USER') or 'guest'
    HOTSPOT_PASS = os.environ.get('HOTSPOT_PASS') or 'secret'
    COMPANY_NAME = os.environ.get('COMPANY_NAME')
