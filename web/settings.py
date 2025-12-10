import os
from environs import Env
from flask import Flask

from core.config import DEBUG
from core.config.language import LANGUAGE_CONTENT, LANGUAGE_DEFAULT
from core.config.logging import LOG_LEVEL, configure_logger

env = Env()
env.read_env()

basedir = os.path.abspath(os.path.dirname(__file__))


class Config:
    @classmethod
    def init_app(cls, app: Flask):
        cls.DEBUG = DEBUG
        cls.LOG_LEVEL = LOG_LEVEL
        cls.LANGUAGE_CONTENT = LANGUAGE_CONTENT
        cls.LANGUAGE_DEFAULT = LANGUAGE_DEFAULT

        configure_logger(app.logger, cls.LOG_LEVEL)

        with env.prefixed("FLASK_"):
            cls.SECRET_KEY = env.str('SECRET_KEY', None)

        app.config.from_object(cls)
