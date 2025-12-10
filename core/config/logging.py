from logging import Logger, getLogger
import logging

from core.config import DEBUG, SETTINGS

from environs import Env

env = Env()
env.read_env()

level_name = SETTINGS.get('log_level', 'DEBUG' if DEBUG else 'WARNING')
mapping = logging.getLevelNamesMapping()
level = mapping.get(level_name.upper())

LOG_LEVEL = env.log_level('LOG_LEVEL', level)

def is_gunicorn():
    return env.str('SERVER_SOFTWARE', '').startswith('gunicorn')

def configure_logger(logger: Logger, level=None):
    if is_gunicorn():
        gunicorn_error_logger = getLogger('gunicorn.error')
        logger.handlers = gunicorn_error_logger.handlers
        logger.setLevel(gunicorn_error_logger.level)
        logger.propagate = False
    else:
        if level is None:
            level = LOG_LEVEL

        logger.setLevel(level)
        handler = logging.StreamHandler()

        if logger.hasHandlers():
            for h in logger.handlers:
                if isinstance(h, logging.StreamHandler):
                    handler = h
                    break
        
        fmt = '[%(asctime)s] [%(process)d] [%(levelname)s] [%(name)s] %(message)s'
        datefmt = '%Y-%m-%d %H:%M:%S %z'
        formatter = logging.Formatter(fmt, datefmt)
        handler.setFormatter(formatter)

        if not logger.hasHandlers():
            logger.addHandler(handler)

        logger.propagate = False
