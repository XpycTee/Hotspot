from redis import Redis
from core.bootstrap.env import REDIS_URL
from core.config.models import AppConfig
from core.config.store import ConfigRuntime
from core.utils import json


_runtime: ConfigRuntime | None = None

def init_config() -> AppConfig:
    global _runtime
    _runtime = ConfigRuntime()
    return _runtime.get()

def get_config() -> AppConfig:
    return _runtime.get()

def config_listener():
    redis = Redis.from_url(REDIS_URL, decode_responses=True)
    pubsub = redis.pubsub()
    pubsub.subscribe("config:update")

    for msg in pubsub.listen():
        if msg["type"] == "message":
            data = json.loads(msg["data"])
            if _runtime.version < data.get('version'):
                _runtime.reload()
