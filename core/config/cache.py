from urllib.parse import ParseResult, urlparse
from environs import Env

env = Env(prefix="HOTSPOT_CACHE_")
env.read_env()

CACHE_URL = env.str("URL", default='memcached+unix:///tmp/memcached.sock')
