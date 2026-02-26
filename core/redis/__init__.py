from contextlib import contextmanager

from core.redis.cache import RedisCache

@contextmanager
def get_cache():
    conn = RedisCache()

    yield conn

    conn.close()
