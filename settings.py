import os
import hashlib

import yaml

from app.sms.huawei import HuaweiSMSSender
from app.sms.mikrotik import MikrotikSMSSender
from app.sms.smsru import SMSRUSender
from app.sms import DebugSender

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
        "DEBUG": DebugSender,
    }
    sender = senders.get(sender_name)
    SENDER = sender(sender_config)

    with open("config/employees.yaml", "rb") as emp_config_file:
        file_contents = emp_config_file.read()
        EMPLOYEES = yaml.safe_load(file_contents).get('employees', [])

        EMP_HASH = hashlib.md5(file_contents).hexdigest()

    with open("config/hotspot_users.yaml", "r") as users_config_file:
        HOTSPOT_USERS = yaml.safe_load(users_config_file).get('users', {})
    with open("config/blacklist.yaml", "r") as bl_config_file:
        BLACKLIST = yaml.safe_load(bl_config_file).get('blacklist', [])

    HOTSPOT_USER = os.environ.get('HOTSPOT_USER') or 'guest'
    HOTSPOT_PASS = os.environ.get('HOTSPOT_PASS') or 'secret'
    COMPANY_NAME = os.environ.get('COMPANY_NAME')
