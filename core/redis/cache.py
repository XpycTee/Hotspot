import json

from redis import Redis

from core.bootstrap.env import REDIS_URL


TYPE_SERIALIZERS = {
    int:    ("int", str, int),
    bool:   ("bool", lambda v: "1" if v else "0", lambda v: v == "1"),
    float:  ("float", str, float),
    str:    ("str", str, str),
    dict:   ("json", json.dumps, json.loads),
    list:   ("json", json.dumps, json.loads),
}


class RedisCache:
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

    def _encode(self, value):
        for py_type, (name, serializer, _) in TYPE_SERIALIZERS.items():
            if type(value) == py_type:
                return f"@{name}:{serializer(value)}"
        raise TypeError(f"Unsupported type: {type(value)}")

    def _decode(self, raw: bytes | str):
        if raw is None:
            return None

        if isinstance(raw, bytes):
            raw = raw.decode("utf-8")

        if not raw.startswith("@"):
            return raw  # fallback для легаси данных

        type_name, value = raw[1:].split(":", 1)

        for _, (name, _, deserializer) in TYPE_SERIALIZERS.items():
            if name == type_name:
                return deserializer(value)

        raise ValueError(f"Unknown type: {type_name}")
