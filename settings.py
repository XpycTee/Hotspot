import json
import os
import hashlib
from datetime import timedelta

import yaml

from app.sms.huawei import HuaweiSMSSender
from app.sms.mikrotik import MikrotikSMSSender
from app.sms.smsru import SMSRUSender
from app.sms import DebugSender
import bcrypt

basedir = os.path.abspath(os.path.dirname(__file__))


def convert_delay(delay):
    suffixes = {
        'w': 'weeks',
        'd': 'days',
        'h': 'hours',
        'm': 'minutes',
        's': 'seconds'
    }

    amount, suffix = (int(delay[:-1]), delay[-1]) if delay[-1] in suffixes else (int(delay), 'h')
    return timedelta(**{suffixes[suffix]: amount})


class Config:
    with open("config/settings.yaml", "r", encoding="utf-8") as settings_file:
        settings = yaml.safe_load(settings_file).get('settings')

    admin = settings.get('admin')
    admin_username = admin['user'].get('username')
    admin_password = admin['user'].get('password')

    # Check if the password is already hashed
    try:
        bcrypt.checkpw(b"test", admin_password.encode('utf-8'))
    except ValueError:
        # If not hashed, hash the password
        admin_password = bcrypt.hashpw(admin_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

        # Update the settings with the hashed password
        settings['admin']['user']['password'] = admin_password

        # Save the updated settings back to the YAML file
        with open("config/settings.yaml", "w", encoding="utf-8") as settings_file:
            yaml.dump({'settings': settings}, settings_file, default_flow_style=False, allow_unicode=True)

    ADMIN = {'username': admin_username, 'password': admin_password}

    with open("config/blacklist.yaml", "r", encoding="utf-8") as bl_config_file:
        BLACKLIST = yaml.safe_load(bl_config_file).get('blacklist', [])

    with open("config/employees.yaml", "rb") as emp_config_file:
        file_contents = emp_config_file.read()

    MAX_LOGIN_ATTEMPTS = 5
    LOCKOUT_TIME = 15

    EMPLOYEES = yaml.safe_load(file_contents).get('employees', [])
    EMP_HASH = hashlib.md5(file_contents).hexdigest()

    with open(f"app/language/{settings.get('language', 'en-US')}.json", "r", encoding='utf-8') as lang_file:
        LANGUAGE_CONTENT = json.load(lang_file)

    SQLALCHEMY_DATABASE_URI = settings.get('db_url', f"sqlite:///{os.path.join(basedir, 'config/hotspot.db')}")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    HOTSPOT_USERS = settings.get('hotspot_users', {})

    HOTSPOT_USERS['guest']['delay'] = convert_delay(HOTSPOT_USERS['guest']['delay'])
    HOTSPOT_USERS['employee']['delay'] = convert_delay(HOTSPOT_USERS['employee']['delay'])

    COMPANY_NAME = settings.get('company_name')

    DEBUG = settings.get('debug')

    senders = {
        "smsru": SMSRUSender,
        "mikrotik": MikrotikSMSSender,
        "huawei": HuaweiSMSSender
    }
    sender_config = settings.get('sender', {})
    sender = senders.get(sender_config.get('type'), DebugSender)
    if sender_config:
        SENDER = sender(**sender_config)
    else:
        SENDER = sender()
