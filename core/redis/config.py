import json

from redis import Redis

from core.config.redis import REDIS_URL


class RadiusConfigStore:
    def __init__(self):
        self.r = Redis.from_url(REDIS_URL, decode_responses=True)

    def load(self):
        data = self.r.get("config:radius")
        return json.loads(data) if data else {}

    def save(self, config):
        self.r.set("config:radius", json.dumps(config))
        self.r.publish("config:update", "radius")


class ConfigListener:
    def __init__(self, on_reload):
        self.r = Redis.from_url(REDIS_URL, decode_responses=True)
        self.pubsub = self.r.pubsub()
        self.on_reload = on_reload

    def run(self):
        self.pubsub.subscribe("config:update")
        for msg in self.pubsub.listen():
            if msg["type"] == "message":
                self.on_reload(msg["data"])
