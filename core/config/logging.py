from logging import Logger, getLogger
import logging

from core.config import CONFIG


def configure_logger(logger: Logger, level=None):
    if CONFIG.logging.is_gunicorn:
        gunicorn_error_logger = getLogger('gunicorn.error')
        logger.handlers = gunicorn_error_logger.handlers
        logger.setLevel(gunicorn_error_logger.level)
        logger.propagate = False
    else:
        if level is None:
            level = CONFIG.logging.level

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
