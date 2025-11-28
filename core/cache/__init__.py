from cachelib import BaseCache
from core.cache.config import configure_cache
from core.config.cache import CACHE_URL


cache = configure_cache(CACHE_URL)

def get_cache() -> BaseCache:
    return cache
