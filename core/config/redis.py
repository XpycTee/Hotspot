from urllib.parse import urlparse
from environs import Env

from core.config import SETTINGS

env = Env(prefix='HOTSPOT_REDIS_')
env.read_env()

DEFAULT_REDIS_URL = 'unix:///tmp/redis.sock?db=0'

REDIS_URL = env.str('URL', SETTINGS.get('redis_url', DEFAULT_REDIS_URL))
