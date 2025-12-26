import threading
from core.bootstrap.env import REDIS_URL
from core.config import CONFIG
from core.config.loader import ConfigLoader
from core.config.store import ConfigStore
from core.utils import json
from core.logging import get_logger


logger = get_logger('core.config.listener')

from redis import Redis


from typing import Callable

config_lock = threading.RLock()


class ConfigListener:
    def __init__(self, handler: Callable | None = None):
        self._r = Redis.from_url(REDIS_URL, decode_responses=True)
        self._pubsub = self._r.pubsub()
        self._store = ConfigStore(self._r)
        if isinstance(handler, Callable):
            self._handler = handler

    def _handler(self, update: dict):
        with config_lock:
            logger.debug(update)
            up_version = update.get('version')
            if up_version <= CONFIG.version:
                return  # устаревшее событие

            new_cfg = self._store.load()
            logger.debug(new_cfg)

            ConfigLoader(new_cfg).update(CONFIG)

    def run(self):
        self._pubsub.subscribe('config:update')
        for msg in self._pubsub.listen():
            if msg["type"] == "message":
                data = json.loads(msg["data"])
                self._handler(data)
