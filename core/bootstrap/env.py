import logging
import os
from environs import Env


DEFAULT_DB_URL = 'sqlite:///hotspot.db'
DEFAULT_REDIS_URL = 'unix:///tmp/redis.sock?db=0'
DEFAULT_LOG_LEVEL = logging.WARNING

env = Env(prefix="HOTSPOT_")
env.read_env()

DB_URL = env.str("DB_URL", DEFAULT_DB_URL)
REDIS_URL = env.str("REDIS_URL", DEFAULT_REDIS_URL)
LOG_LEVEL = env.log_level("LOG_LEVEL", DEFAULT_LOG_LEVEL)
IS_GUNICORN = os.environ.get('SERVER_SOFTWARE', '').startswith('gunicorn')
