# logger.py
from flask import current_app

def debug(msg, *args, **kwargs):
    current_app.logger.debug(msg, *args, **kwargs)

def info(msg, *args, **kwargs):
    current_app.logger.info(msg, *args, **kwargs)

def warning(msg, *args, **kwargs):
    current_app.logger.warning(msg, *args, **kwargs)

def error(msg, *args, **kwargs):
    current_app.logger.error(msg, *args, **kwargs)
