from logging import Logger, getLogger
import logging

from environs import Env

env = Env()
env.read_env()


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
            level = env.log_level("LOG_LEVEL", logging.WARNING)

        logger.setLevel(level)
        if logger.hasHandlers():
            for h in logger.handlers:
                if isinstance(h, logging.StreamHandler):
                    handler = h
                    break
                else:
                    handler = logging.StreamHandler()
        else:
            handler = logging.StreamHandler()

        formatter = logging.Formatter("[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s")
        handler.setFormatter(formatter)

        if not logger.hasHandlers():
            logger.addHandler(handler)

        logger.propagate = False
