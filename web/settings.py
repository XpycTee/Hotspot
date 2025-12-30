import logging
import os
from environs import Env
from flask import Flask

from core.bootstrap.env import LOG_LEVEL
from core.config import get_config
from core.bootstrap.logging import configure_logger

env = Env()
env.read_env()

basedir = os.path.abspath(os.path.dirname(__file__))


class Config:
    @classmethod
    def init_app(cls, app: Flask):
        config = get_config()
        cls.DEBUG = LOG_LEVEL == logging.DEBUG
        cls.LOG_LEVEL = LOG_LEVEL
        cls.LANGUAGE_CONTENT = config.language.content
        cls.LANGUAGE_DEFAULT = config.language.name

        configure_logger(app.logger, cls.LOG_LEVEL)

        with env.prefixed("FLASK_"):
            cls.SECRET_KEY = env.str('SECRET_KEY', None)

        app.config.from_object(cls)
