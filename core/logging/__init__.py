

from logging import getLogger

from core.config.logging import configure_logger


def get_logger(name: str):
    logger = getLogger(name)
    configure_logger(logger)
    return logger
