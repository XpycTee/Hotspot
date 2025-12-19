from redis import Redis

from core.config.redis import REDIS_URL


cache = Redis.from_url(REDIS_URL, decode_responses=True)
