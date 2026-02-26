from dataclasses import is_dataclass
from threading import Lock
from time import time

from typing import Any, Callable
from uuid import UUID

from redis import Redis
from redis.exceptions import RedisError

from core.bootstrap.env import REDIS_URL
from core.logging import get_logger
from core.utils import json


class _InMemoryRedis:
    def __init__(self):
        self._data: dict[str, str] = {}
        self._expires: dict[str, float] = {}
        self._lock = Lock()

    def ping(self):
        return True

    def close(self):
        return None

    def _is_expired(self, key: str) -> bool:
        exp = self._expires.get(key)
        if exp is None:
            return False
        if time() >= exp:
            self._data.pop(key, None)
            self._expires.pop(key, None)
            return True
        return False

    def set(self, key: str, value, ex=None):
        with self._lock:
            self._data[key] = str(value)
            if ex is not None:
                self._expires[key] = time() + ex
            else:
                self._expires.pop(key, None)
        return True

    def get(self, key: str):
        with self._lock:
            if self._is_expired(key):
                return None
            return self._data.get(key)

    def delete(self, key: str):
        with self._lock:
            self._expires.pop(key, None)
            return 1 if self._data.pop(key, None) is not None else 0

    def incr(self, key: str, amount=1):
        with self._lock:
            if self._is_expired(key):
                current = 0
                exp = None
            else:
                current = int(self._data.get(key, "0"))
                exp = self._expires.get(key)
            updated = current + amount
            self._data[key] = str(updated)
            if exp is not None:
                self._expires[key] = exp
            return updated

    def exists(self, key: str):
        with self._lock:
            if self._is_expired(key):
                return 0
            return 1 if key in self._data else 0

    def flushdb(self):
        with self._lock:
            self._data.clear()
            self._expires.clear()
        return True

    def eval(self, script, _numkeys, key):
        with self._lock:
            if self._is_expired(key):
                return None
            value = self._data.get(key)
            if value is not None:
                del self._data[key]
                self._expires.pop(key, None)
            return value

    def getdel(self, key: str):
        with self._lock:
            if self._is_expired(key):
                return None
            value = self._data.get(key)
            if value is not None:
                del self._data[key]
                self._expires.pop(key, None)
            return value


class RedisCache:
    _memory_backend = _InMemoryRedis()
    SERIALIZER_RULES = [
        (lambda v: isinstance(v, bool),  "bool",  lambda v: "1" if v else "0", lambda v: v == "1"),
        (lambda v: isinstance(v, int),   "int",   str, int),
        (lambda v: isinstance(v, float), "float", str, float),
        (lambda v: isinstance(v, str),   "str",   str, str),
        (lambda v: isinstance(v, UUID),  "uuid",  str, UUID),
        (lambda v: isinstance(v, dict),  "json",  json.dumps_str, json.loads),
        (lambda v: isinstance(v, list),  "json",  json.dumps_str, json.loads),
        (lambda v: is_dataclass(v),      "json",  json.dumps_str, json.loads),
    ]
    
    def __init__(self, url=None):
        self._url = url if url is not None else REDIS_URL
        self._serializers = list(self.SERIALIZER_RULES)
        self._logger = get_logger("core.redis.cache")
        try:
            self.r = Redis.from_url(self._url, decode_responses=True)
            self.r.ping()
        except RedisError:
            self.r = self._memory_backend
            self._logger.warning("Redis unavailable, using in-memory cache backend", exc_info=True)
        except OSError:
            self.r = self._memory_backend
            self._logger.warning("Redis unavailable, using in-memory cache backend", exc_info=True)

    def close(self):
        self.r.close()

    def set(self, key: str, value, timeout=None):
        """
        Set key to hold the string value. 
        If key already holds a value, it is overwritten, regardless of its type. 
        Any previous time to live associated with the key is discarded on successful SET operation.
        """
        self.r.set(key, self._encode(value), ex=timeout)

    def set_raw(self, key: str, value, timeout=None):
        self.r.set(key, value, ex=timeout)

    def get(self, key: str, default=None):
        val = self.r.get(key)
        if val is None:
            return default
        return self._decode(val)

    def get_raw(self, key: str, default=None):
        val = self.r.get(key)
        if val is None:
            return default
        return val

    def delete(self, key: str):
        self.r.delete(key)

    def incr(self, key: str, amount=1):
        return self.r.incr(key, amount)

    def has(self, key: str):
        return self.r.exists(key) == 1

    def clear(self):
        self.r.flushdb()

    def pop(self, key: str):
        if hasattr(self.r, "getdel"):
            return self._decode(self.r.getdel(key))

        return self._decode(self.r.eval("""
            local v = redis.call('GET', KEYS[1])
            if v then redis.call('DEL', KEYS[1]) end
            return v
        """, 1, key))

    def register_serializer(self, check: Callable[[Any], bool], name: str, serializer, deserializer):
        self._serializers.append((check, name, serializer, deserializer))

    def _encode(self, value: Any) -> str:
        for check, name, serializer, _ in self._serializers:
            if check(value):
                data = serializer(value)
                return f"@{name}:{data}"
            
        raise TypeError(f"Unsupported type: {type(value)}")

    def _decode(self, raw: bytes | str):
        if raw is None:
            return None

        if isinstance(raw, bytes):
            raw = raw.decode("utf-8")

        if not raw.startswith("@"):
            return raw  # fallback для легаси данных

        type_name, value = raw[1:].split(":", 1)

        for _, name, _, deserializer in self._serializers:
            if name == type_name:
                return deserializer(value)

        raise ValueError(f"Unknown type: {type_name}")
