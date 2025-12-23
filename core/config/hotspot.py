from core.config import get_config
from core.config.loader import ConfigLoader
from core.config.models import HotspotConfig


def get_hotspot_config() -> HotspotConfig:
    config = get_config()
    raw = config.get('data', {})
    version = config.get('version', 0)
    data = ConfigLoader(raw, version).hotspot()
    return data


config = get_hotspot_config()
ONLINE_TIMEOUT = config.online_timeout
