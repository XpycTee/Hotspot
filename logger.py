# logger.py
from logging import Logger, getLogger
from flask import current_app

def debug(msg, *args, **kwargs):
    current_app.logger.debug(msg, *args, **kwargs)

def info(msg, *args, **kwargs):
    current_app.logger.info(msg, *args, **kwargs)

def warning(msg, *args, **kwargs):
    current_app.logger.warning(msg, *args, **kwargs)

def error(msg, *args, **kwargs):
    current_app.logger.error(msg, *args, **kwargs)

def configure_logger(logger: Logger):
    gunicorn_error_logger = getLogger('gunicorn.error')
    logger.handlers = gunicorn_error_logger.handlers
    logger.setLevel(gunicorn_error_logger.level)
    logger.propagate = False