import logging
import os
from environs import Env
from flask import Flask

from core.config import CONFIG
from core.config.logging import configure_logger

env = Env()
env.read_env()

basedir = os.path.abspath(os.path.dirname(__file__))


class Config:
    @classmethod
    def init_app(cls, app: Flask):
        cls.DEBUG = CONFIG.logging.level == logging.DEBUG
        cls.LOG_LEVEL = CONFIG.logging.level
        cls.LANGUAGE_CONTENT = CONFIG.language.content
        cls.LANGUAGE_DEFAULT = CONFIG.language.name

        configure_logger(app.logger, cls.LOG_LEVEL)

        with env.prefixed("FLASK_"):
            cls.SECRET_KEY = env.str('SECRET_KEY', None)

        app.config.from_object(cls)
