from environs import Env


DEFAULT_DB_URL = 'sqlite:///hotspot.db'
DEFAULT_REDIS_URL = 'unix:///tmp/redis.sock?db=0'

env = Env(prefix="HOTSPOT_")
env.read_env()

DB_URL = env.str("DB_URL", DEFAULT_DB_URL)
REDIS_URL = env.str("REDIS_URL", DEFAULT_REDIS_URL)
