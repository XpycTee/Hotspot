from dataclasses import is_dataclass

from typing import Any, Callable
from uuid import UUID

from redis import Redis

from core.bootstrap.env import REDIS_URL
from core.utils import json


class RedisCache:
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
    
    def __init__(self):
        self.r = Redis.from_url(REDIS_URL, decode_responses=True)

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
        val = self.r.get(key) or default
        return self._decode(val)

    def get_raw(self, key: str, default=None):
        val = self.r.get(key) or default
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
        return self._decode(self.r.eval("""
            local v = redis.call('GET', KEYS[1])
            if v then redis.call('DEL', KEYS[1]) end
            return v
        """, 1, key))

    def register_serializer(self, check: Callable[[Any], bool], name: str, serializer, deserializer):
        self.SERIALIZER_RULES.append((check, name, serializer, deserializer))

    def _encode(self, value: Any) -> str:
        for check, name, serializer, _ in self.SERIALIZER_RULES:
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

        for _, name, _, deserializer in self.SERIALIZER_RULES:
            if name == type_name:
                return deserializer(value)

        raise ValueError(f"Unknown type: {type_name}")
