import os
from urllib.parse import urlparse
from cachelib import FileSystemCache, MemcachedCache, RedisCache, SimpleCache
from environs import Env

from core.logging.logger import logger

env = Env(prefix="HOTSPOT_CACHE_")
env.read_env()

CACHE_URL = env.str("URL", default='memcached+unix:///tmp/memcached.sock')


def configure_cache(url='simple', default_timeout=300):
    cache_types = {
        'redis': RedisCache,
        'memcached': MemcachedCache,
        'file': FileSystemCache,
        'simple': SimpleCache
    }
    
    if url == 'simple':
        Cache = cache_types.get('simple')
        return Cache(default_timeout=default_timeout)

    parsed_url = urlparse(url)
    scheme = parsed_url.scheme

    if scheme == 'redis':
        Cache = cache_types.get('redis')
        port = parsed_url.port or 6379
        host = parsed_url.hostname
        password = parsed_url.password

        path = parsed_url.path[1:]
        try:
            db = int(path)
        except ValueError as e:
            db = 0
            logger.error(e)

        return Cache(host=host, port=port, password=password, db=db, default_timeout=default_timeout)
    elif scheme == 'memcached+unix':
        server = f"unix:{parsed_url.path}"
        Cache = cache_types.get('memcached')
        return Cache(servers=[server], default_timeout=default_timeout)
    elif scheme == 'memcached':
        server = f"{parsed_url.hostname}:{parsed_url.port}"
        Cache = cache_types.get('memcached')
        return Cache(servers=[server], default_timeout=default_timeout)
    elif scheme == 'file':
        Cache = cache_types.get('file')
        cwd = os.getcwd()
        cache_path = cwd+parsed_url.path
        return Cache(cache_path, default_timeout=default_timeout)
    else:
        raise NotImplementedError(f"Not implemented cache {scheme}")
