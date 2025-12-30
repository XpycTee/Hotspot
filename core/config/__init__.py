from typing import Callable
from redis import Redis
from core.bootstrap.env import REDIS_URL
from core.config.models import AppConfig
from core.config.store import ConfigRuntime, ConfigLoader
from core.logging import get_logger
from core.utils import json


_runtime: ConfigRuntime | None = None
_backend: str | None = None


def init_config(backend: str) -> AppConfig:
    global _runtime, _backend

    if backend not in ('web', 'radius'):
        raise ValueError(f'Unknown backend: {backend}')
    
    if _backend is not None:
        assert _backend in ('web', 'radius'), _backend

    if backend == 'radius':
        _runtime = ConfigRuntime()
        _backend = backend
        return _runtime.get()
    
    if backend == 'web':
        _backend = backend
        return ConfigLoader().load()
    
    raise ValueError(f'Unknown backend: {backend}')


def get_config():
    if _backend is None:
        raise RuntimeError('Config backend not initialized')

    if _backend == 'radius':
        return _runtime.get()

    if _backend == 'web':
        return ConfigLoader().load()

    raise RuntimeError(f'Unknown config backend: {_backend}')


def runtime_listener(handler: Callable):
    logger = get_logger('Config listener')
    redis = Redis.from_url(REDIS_URL, decode_responses=True)
    pubsub = redis.pubsub()
    pubsub.subscribe("config:update")

    for msg in pubsub.listen():
        if msg["type"] == "message":
            data = json.loads(msg["data"])
            logger.debug(data)
            if _runtime.version < data.get('version'):
                _runtime.force_reload()
                handler()
