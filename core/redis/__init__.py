from core.redis.cache import RedisCache
from core.redis.config import ConfigListener, RadiusConfigStore
from core.logging.logger import logger

cache = RedisCache()

config_store = RadiusConfigStore()
config_listener = ConfigListener(logger.debug)
