from logging import getLogger

from core.config.logging import configure_logger


logger = getLogger("RADIUS Server")

configure_logger(logger)