import json
import logging
import os
from datetime import timedelta
from urllib.parse import urlparse

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
    LANGUAGE_FOLDER = "app/static/language"
    DEFAULT_ADMIN_USERNAME = 'admin'
    DEFAULT_ADMIN_PASSWORD = 'admin'
    DEFAULT_ADMIN_MAX_LOGIN_ATTEMPTS = 3
    DEFAULT_ADMIN_LOCKOUT_TIME = 5
    DEFAULT_COMPANY_NAME = 'Default Company'
    DEFAULT_DB_URL = f"sqlite:///{os.path.join(basedir, 'config/hotspot.db')}"
    DEFAULT_CAHCE_URL = "memcached://localhost:11211"
    USER_TYPES = ['guest', 'employee']
    CACHE_TYPES = {
        'redis': "RedisCache",
        'memcached': "MemcachedCache",
        'saslmemcached': "SASLMemcachedCache",
        'file': "FileSystemCache",
        'simple': "SimpleCache"
    }
    SMS_SENDERS = {
        "smsru": SMSRUSender,
        "mikrotik": MikrotikSMSSender,
        "huawei": HuaweiSMSSender
    }

    # Переменные класса для хранения конфигурации
    ADMIN = None
    SECRET_KEY = None
    CACHE_TYPE = None
    CACHE_REDIS_URL = None
    CACHE_MEMCACHED_USERNAME = None
    CACHE_MEMCACHED_PASSWORD = None
    CACHE_MEMCACHED_SERVERS = None
    CACHE_DIR = None
    LANGUAGE_DEFAULT = None
    LANGUAGE_CONTENT = None
    SQLALCHEMY_DATABASE_URI = None
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    HOTSPOT_USERS = None
    COMPANY_NAME = None
    DEBUG = None
    SENDER = None

    @classmethod
    def init_app(cls, app):
        cls.settings = cls.load_settings()
        cls.ADMIN = cls.configure_admin()
        cls.SECRET_KEY = os.environ.get('FLASK_SECRET_KEY', cls.settings.get('flask_secret_key'))
        logging.debug(cls.SECRET_KEY)
        cls.LANGUAGE_DEFAULT = os.environ.get('HOTSPOT_LANGUAGE', cls.settings.get('language', 'en'))
        cls.LANGUAGE_CONTENT = cls.load_language_files()
        cls.configure_cache()
        cls.SQLALCHEMY_DATABASE_URI = os.environ.get('HOTSPOT_DB_URL', cls.settings.get('db_url', cls.DEFAULT_DB_URL))
        cls.HOTSPOT_USERS = cls.configure_hotspot_users()
        cls.COMPANY_NAME = os.environ.get('HOTSPOT_COMPANY_NAME', cls.settings.get('company_name', cls.DEFAULT_COMPANY_NAME))
        cls.DEBUG = os.environ.get('DEBUG', cls.settings.get('debug', False))
        cls.SENDER = cls.configure_sms_sender()

        app.config.from_object(cls)

    @classmethod
    def load_settings(cls):
        with open(cls.SETTINGS_FILE_PATH, "r", encoding="utf-8") as settings_file:
            return yaml.safe_load(settings_file).get('settings', {})

    @classmethod
    def configure_cache(cls):
        url = os.environ.get('CACHE_URL', cls.settings.get('cache_url', cls.DEFAULT_CAHCE_URL))
        if url == 'simple':
            cls.CACHE_TYPE = cls.CACHE_TYPES.get(url)
            return

        parsed_url = urlparse(url)

        scheme = parsed_url.scheme
        cls.CACHE_TYPE = cls.CACHE_TYPES.get(scheme)

        if scheme == 'redis':
            cls.CACHE_REDIS_URL = url
        elif scheme == 'memcached':
            server = f"{parsed_url.hostname}:{parsed_url.port}"
            cls.CACHE_MEMCACHED_SERVERS = [server]
        elif scheme == 'saslmemcached':
            cls.CACHE_MEMCACHED_USERNAME = parsed_url.username
            cls.CACHE_MEMCACHED_PASSWORD = parsed_url.password
            server = f"{parsed_url.hostname}:{parsed_url.port}"
            cls.CACHE_MEMCACHED_SERVERS = [server]
        elif scheme == 'file':
            cls.CACHE_DIR = parsed_url.path
        else:
            raise NotImplementedError(f"Not implemented cache {scheme}")

    @classmethod
    def configure_admin(cls):
        admin_settings = cls.settings.get('admin', {})
        admin_user = admin_settings.get('user', {})
        username = os.environ.get('HOTSPOT_ADMIN_USERNAME', admin_user.get('username', cls.DEFAULT_ADMIN_USERNAME))
        password = os.environ.get('HOTSPOT_ADMIN_PASSWORD', admin_user.get('password', cls.DEFAULT_ADMIN_PASSWORD))
        max_login_attempts = os.environ.get('HOTSPOT_ADMIN_MAX_LOGIN_ATTEMPTS', admin_settings.get('max_login_attempts', cls.DEFAULT_ADMIN_MAX_LOGIN_ATTEMPTS))
        lockout_time = os.environ.get('HOTSPOT_ADMIN_LOCKOUT_TIME', admin_settings.get('lockout_time', cls.DEFAULT_ADMIN_LOCKOUT_TIME))
        password_hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        return {
            'username': username, 
            'password': password_hashed, 
            'max_login_attempts': int(max_login_attempts), 
            'lockout_time': int(lockout_time)
        }

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
        sender_class = cls.SMS_SENDERS.get(sender_type, DebugSender)

        # Собираем все параметры из переменных окружения и конфигурации
        sender_params = {**sender_config}
        for key, value in os.environ.items():
            if key.startswith('HOTSPOT_SENDER_'):
                param_name = key[len('HOTSPOT_SENDER_'):].lower()
                sender_params[param_name] = value

        # Инициализация отправителя с универсальными параметрами
        return sender_class(**sender_params)
        