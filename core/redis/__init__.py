from contextlib import contextmanager

from core.redis.cache import RedisCache

@contextmanager
def get_cache():
    cache = RedisCache()

    yield cache

    cache.close()
