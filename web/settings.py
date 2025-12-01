import json
import logging
import os
from environs import Env
from flask import Flask
import bcrypt

from core.config.logging import configure_logger

env = Env()
env.read_env()

basedir = os.path.abspath(os.path.dirname(__file__))


class Config:
    LANGUAGE_FOLDER = "web/static/language"
    DEFAULT_LANGUAGE_DEFAULT = 'en'
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
        cls.DEBUG = env.bool('DEBUG', False)
        cls.LOG_LEVEL = env.log_level('LOG_LEVEL', logging.INFO)

        configure_logger(app.logger, cls.LOG_LEVEL)

        with env.prefixed("FLASK_"):
            cls.SECRET_KEY = env.str('SECRET_KEY', None)

        with env.prefixed("HOTSPOT_"):
            cls.ADMIN = cls.configure_admin()
            with env.prefixed("WEB_"):
                cls.LANGUAGE_DEFAULT = os.environ.get('LANGUAGE', cls.DEFAULT_LANGUAGE_DEFAULT)
                cls.COMPANY_NAME = os.environ.get('COMPANY_NAME', cls.DEFAULT_COMPANY_NAME)

        cls.LANGUAGE_CONTENT = cls.load_language_files()

        app.config.from_object(cls)

    @classmethod
    def configure_admin(cls):
        with env.prefixed("ADMIN_"):
            username = env.str('USERNAME', cls.DEFAULT_ADMIN_USERNAME)
            password = env.str('PASSWORD', cls.DEFAULT_ADMIN_PASSWORD)
            max_login_attempts = env.int('MAX_LOGIN_ATTEMPTS', cls.DEFAULT_ADMIN_MAX_LOGIN_ATTEMPTS)
            lockout_time = env.int('LOCKOUT_TIME', cls.DEFAULT_ADMIN_LOCKOUT_TIME)
        
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
       