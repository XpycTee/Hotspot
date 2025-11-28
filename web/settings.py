import json
import logging
import os
from environs import Env
from flask import Flask
import yaml
import bcrypt

from core.config.logging import configure_logger

env = Env()
env.read_env()

basedir = os.path.abspath(os.path.dirname(__file__))


class Config:
    SETTINGS_FILE_PATH = "config/settings.yaml"
    LANGUAGE_FOLDER = "web/static/language"
    DEFAULT_ADMIN_USERNAME = 'admin'
    DEFAULT_ADMIN_PASSWORD = 'admin'
    DEFAULT_ADMIN_MAX_LOGIN_ATTEMPTS = 3
    DEFAULT_ADMIN_LOCKOUT_TIME = 5
    DEFAULT_COMPANY_NAME = 'Default Company'

    # Переменные класса для хранения конфигурации
    ADMIN = None
    SECRET_KEY = None
    LANGUAGE_DEFAULT = None
    LANGUAGE_CONTENT = None
    COMPANY_NAME = None
    DEBUG = None

    @classmethod
    def init_app(cls, app: Flask):
        cls.settings = cls.load_settings()
        cls.DEBUG = env.bool('DEBUG', cls.settings.get('debug', False))
        cls.LOG_LEVEL = env.log_level('LOG_LEVEL', logging.INFO)

        configure_logger(app.logger, cls.LOG_LEVEL)

        with env.prefixed("FLASK_"):
            cls.SECRET_KEY =env.str('SECRET_KEY', cls.settings.get('flask_secret_key'))

        with env.prefixed("HOTSPOT_"):
            cls.ADMIN = cls.configure_admin()
            with env.prefixed("WEB_"):
                cls.LANGUAGE_DEFAULT = os.environ.get('LANGUAGE', cls.settings.get('language', 'en'))
                cls.COMPANY_NAME = os.environ.get('COMPANY_NAME', cls.settings.get('company_name', cls.DEFAULT_COMPANY_NAME))

        cls.LANGUAGE_CONTENT = cls.load_language_files()

        app.config.from_object(cls)

    @classmethod
    def load_settings(cls):
        with open(cls.SETTINGS_FILE_PATH, "r", encoding="utf-8") as settings_file:
            return yaml.safe_load(settings_file).get('settings', {})

    @classmethod
    def configure_admin(cls):
        admin_settings = cls.settings.get('admin', {})
        admin_user = admin_settings.get('user', {})
        with env.prefixed("ADMIN_"):
            username = env.str('USERNAME', admin_user.get('username', cls.DEFAULT_ADMIN_USERNAME))
            password = env.str('PASSWORD', admin_user.get('password', cls.DEFAULT_ADMIN_PASSWORD))
            max_login_attempts = env.int('MAX_LOGIN_ATTEMPTS', admin_settings.get('max_login_attempts', cls.DEFAULT_ADMIN_MAX_LOGIN_ATTEMPTS))
            lockout_time = env.int('LOCKOUT_TIME', admin_settings.get('lockout_time', cls.DEFAULT_ADMIN_LOCKOUT_TIME))
        
        password_hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        return {
            'username': username, 
            'password': password_hashed, 
            'max_login_attempts': max_login_attempts, 
            'lockout_time': lockout_time
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
       