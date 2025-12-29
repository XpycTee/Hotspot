from core.config.store import ConfigStore


def get_config():
    return ConfigStore().load()
