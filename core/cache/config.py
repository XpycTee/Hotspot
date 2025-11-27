import logging
import os
from urllib.parse import urlparse

from cachelib import FileSystemCache, MemcachedCache, RedisCache, SimpleCache


CACHE_TYPES = {
    'redis': RedisCache,
    'memcached': MemcachedCache,
    'file': FileSystemCache,
    'simple': SimpleCache
}


def configure_cache(url='simple', default_timeout=300):
    if url == 'simple':
        Cache = CACHE_TYPES.get('simple')
        return Cache(default_timeout=default_timeout)

    parsed_url = urlparse(url)
    scheme = parsed_url.scheme
    
    if scheme == 'redis':
        Cache = CACHE_TYPES.get('redis')
        port = parsed_url.port or 6379
        host = parsed_url.hostname
        password = parsed_url.password

        path = parsed_url.path[1:]
        try:
            db = int(path)
        except ValueError as e:
            db = 0
            logging.error(e)
            
        return Cache(host=host, port=port, password=password, db=db, default_timeout=default_timeout)
    elif scheme == 'memcached+unix':
        server = f"unix:{parsed_url.path}"
        Cache = CACHE_TYPES.get('memcached')
        return Cache(servers=[server], default_timeout=default_timeout)
    elif scheme == 'memcached':
        server = f"{parsed_url.hostname}:{parsed_url.port}"
        Cache = CACHE_TYPES.get('memcached')
        return Cache(servers=[server], default_timeout=default_timeout)
    elif scheme == 'file':
        Cache = CACHE_TYPES.get('file')
        cwd = os.getcwd()
        cache_path = cwd+parsed_url.path
        return Cache(cache_path, default_timeout=default_timeout)
    else:
        raise NotImplementedError(f"Not implemented cache {scheme}")
