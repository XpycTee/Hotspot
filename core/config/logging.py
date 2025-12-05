from logging import Logger, getLogger
import logging

from environs import Env

env = Env()
env.read_env()

LOG_LEVEL = env.log_level("LOG_LEVEL", logging.WARNING)

def is_gunicorn():
    return env.str("SERVER_SOFTWARE", "").startswith("gunicorn")

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

        formatter = logging.Formatter("[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s")
        handler.setFormatter(formatter)

        if not logger.hasHandlers():
            logger.addHandler(handler)

        logger.propagate = False
