import json
import os
from datetime import timedelta

import yaml

from app.sms.huawei import HuaweiSMSSender
from app.sms.mikrotik import MikrotikSMSSender
from app.sms.smsru import SMSRUSender
from app.sms import DebugSender

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

    with open("config/blacklist.yaml", "r", encoding="utf-8") as bl_config_file:
        BLACKLIST = yaml.safe_load(bl_config_file).get('blacklist', [])

    with open(f"config/language/{settings.get('language', 'en-US')}.json", "r", encoding='utf-8') as lang_file:
        LANGUAGE_CONTENT = json.load(lang_file)

    SQLALCHEMY_DATABASE_URI = settings.get('db_url', f"sqlite:///{os.path.join(basedir, 'config/hotspot.db')}")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    HOTSPOT_USERS = settings.get('hotspot_users', {})

    HOTSPOT_USERS['guest']['delay'] = convert_delay(HOTSPOT_USERS['guest']['delay'])
    HOTSPOT_USERS['employee']['delay'] = convert_delay(HOTSPOT_USERS['employee']['delay'])

    COMPANY_NAME = settings.get('company_name')

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
