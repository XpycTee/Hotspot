from typing import Callable
from redis import Redis

from core.bootstrap.env import REDIS_URL
from core.config import ConfigStore
from core.utils import json


class ConfigListener:
    def __init__(self, handelr: Callable, domain: str = 'app'):
        self._r = Redis.from_url(REDIS_URL, decode_responses=True)
        self._domain = domain
        self._pubsub = self._r.pubsub()
        self._handler = handelr
        self._store = ConfigStore(domain, self._r)

    def run(self):
        self._pubsub.subscribe('config:update')
        for msg in self._pubsub.listen():
            if msg["type"] == "message":
                data = json.loads(msg["data"])
                self._handler(data, self._store)
