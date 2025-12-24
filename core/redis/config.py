from typing import Callable
from redis import Redis

from core.bootstrap.env import REDIS_URL
from core.utils import json


class ConfigStore:
    def __init__(self, domain: str, redis: Redis | None = None):
        if redis is None:
            self._r = Redis.from_url(REDIS_URL, decode_responses=True)
        else:
            self._r = redis
        self._domain = domain

    def load(self):
        data = self._r.get(f'app:config:{self._domain}')
        return json.loads(data) if data else {}

    def save(self, config):
        self._r.set(f'app:config:{self._domain}', json.dumps(config))
        self._r.publish(f'config:update:{self._domain}', json.dumps({'version': config.version}))


class ConfigListener:
    def __init__(self, domain: str, handelr: Callable):
        self._r = Redis.from_url(REDIS_URL, decode_responses=True)
        self._domain = domain
        self._pubsub = self._r.pubsub()
        self._handler = handelr
        self._store = ConfigStore(domain, self._r)

    def run(self):
        self._pubsub.subscribe(f'config:update:{self._domain}')
        for msg in self._pubsub.listen():
            if msg["type"] == "message":
                data = json.loads(msg["data"])
                self._handler(data, self._store)
