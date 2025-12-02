import logging
import os
from environs import Env
from flask import Flask

from core.config.language import LANGUAGE_CONTENT, LANGUAGE_DEFAULT
from core.config.logging import configure_logger

env = Env()
env.read_env()

basedir = os.path.abspath(os.path.dirname(__file__))


class Config:
    DEFAULT_COMPANY_NAME = 'Default Company'

    SECRET_KEY = None
    COMPANY_NAME = None
    DEBUG = None
    LANGUAGE_CONTENT = LANGUAGE_CONTENT
    LANGUAGE_DEFAULT = LANGUAGE_DEFAULT

    @classmethod
    def init_app(cls, app: Flask):
        cls.DEBUG = env.bool('DEBUG', False)
        cls.LOG_LEVEL = env.log_level('LOG_LEVEL', logging.INFO)

        configure_logger(app.logger, cls.LOG_LEVEL)

        with env.prefixed("FLASK_"):
            cls.SECRET_KEY = env.str('SECRET_KEY', None)

        with env.prefixed("HOTSPOT_WEB_"):
            cls.COMPANY_NAME = os.environ.get('COMPANY_NAME', cls.DEFAULT_COMPANY_NAME)

        app.config.from_object(cls)
