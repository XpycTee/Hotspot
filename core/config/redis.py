
from core.config import get_config
from core.config.loader import ConfigLoader
from core.config.models import RedisConfig


def get_redis_config() -> RedisConfig:
    raw = get_config()
    data = ConfigLoader(raw).redis()
    return data


redis_config = get_redis_config()
REDIS_URL = redis_config.url
