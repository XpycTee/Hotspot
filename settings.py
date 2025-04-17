import json
import logging
import os
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
    SETTINGS_FILE_PATH = "config/settings.yaml"
    LANGUAGE_FOLDER = "app/language"
    DEFAULT_ADMIN_USERNAME = 'admin'
    DEFAULT_ADMIN_PASSWORD = 'admin'
    DEFAULT_COMPANY_NAME = 'Default Company'
    DEFAULT_DB_URL = f"sqlite:///{os.path.join(basedir, 'config/hotspot.db')}"
    USER_TYPES = ['guest', 'employee']
    SMS_SENDERS = {
        "smsru": SMSRUSender,
        "mikrotik": MikrotikSMSSender,
        "huawei": HuaweiSMSSender
    }

    # Переменные класса для хранения конфигурации
    ADMIN = None
    SECRET_KEY = None
    CACHE_TYPE = "MemcachedCache"
    CACHE_MEMCACHED_SERVERS = ['127.0.0.1:11211']
    LANGUAGE_DEFAULT = None
    LANGUAGE_CONTENT = None
    SQLALCHEMY_DATABASE_URI = None
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    HOTSPOT_USERS = None
    COMPANY_NAME = None
    DEBUG = None
    SENDER = None

    @classmethod
    def init_app(cls):
        cls.settings = cls.load_settings()
        cls.logger = logging.getLogger('gunicorn.error')
        cls.ADMIN = cls.configure_admin()
        cls.SECRET_KEY = os.environ.get('FLASK_SECRET_KEY', cls.settings.get('flask_secret_key'))
        cls.logger.debug(cls.SECRET_KEY)
        cls.LANGUAGE_DEFAULT = os.environ.get('HOTSPOT_LANGUAGE', cls.settings.get('language', 'en'))
        cls.LANGUAGE_CONTENT = cls.load_language_files()
        cls.SQLALCHEMY_DATABASE_URI = os.environ.get('HOTSPOT_DB_URL', cls.settings.get('db_url', cls.DEFAULT_DB_URL))
        cls.HOTSPOT_USERS = cls.configure_hotspot_users()
        cls.COMPANY_NAME = os.environ.get('HOTSPOT_COMPANY_NAME', cls.settings.get('company_name', cls.DEFAULT_COMPANY_NAME))
        cls.DEBUG = os.environ.get('DEBUG', cls.settings.get('debug', False))
        cls.SENDER = cls.configure_sms_sender()

    @classmethod
    def load_settings(cls):
        with open(cls.SETTINGS_FILE_PATH, "r", encoding="utf-8") as settings_file:
            return yaml.safe_load(settings_file).get('settings', {})

    @classmethod
    def configure_admin(cls):
        admin_user = cls.settings.get('admin', {}).get('user', {})
        username = os.environ.get('HOTSPOT_ADMIN_USERNAME', admin_user.get('username', cls.DEFAULT_ADMIN_USERNAME))
        password = os.environ.get('HOTSPOT_ADMIN_PASSWORD', admin_user.get('password', cls.DEFAULT_ADMIN_PASSWORD))
        password_hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        return {'username': username, 'password': password_hashed}

    @classmethod
    def load_language_files(cls):
        language_content = {}
        for filename in os.listdir(cls.LANGUAGE_FOLDER):
            if filename.endswith(".json"):
                file_path = os.path.join(cls.LANGUAGE_FOLDER, filename)
                language_name = os.path.splitext(filename)[0]
                with open(file_path, "r", encoding='utf-8') as lang_file:
                    language_content[language_name] = json.load(lang_file)
        return language_content

    @classmethod
    def configure_hotspot_users(cls):
        hotspot_users = cls.settings.get('hotspot_users', {})
        for user_type in cls.USER_TYPES:
            if user_type in hotspot_users:
                password_env = os.environ.get(f'HOTSPOT_{user_type.upper()}_PASSWORD')
                delay_env = os.environ.get(f'HOTSPOT_{user_type.upper()}_DELAY')
                hotspot_users[user_type]['password'] = password_env or hotspot_users[user_type].get('password')
                hotspot_users[user_type]['delay'] = convert_delay(delay_env or hotspot_users[user_type].get('delay', '1h'))
        return hotspot_users

    @classmethod
    def configure_sms_sender(cls):
        sender_config = cls.settings.get('sender', {})
        sender_type = os.environ.get('HOTSPOT_SENDER_TYPE', sender_config.get('type'))
        sender_url = os.environ.get('HOTSPOT_SENDER_URL', sender_config.get('url'))
        sender_class = cls.SMS_SENDERS.get(sender_type, DebugSender)
        return sender_class(url=sender_url) if sender_url else sender_class()
    