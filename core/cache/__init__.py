from cachelib import BaseCache
from core.cache.config import configure_cache


cache = configure_cache()

def get_cache() -> BaseCache:
    return cache
