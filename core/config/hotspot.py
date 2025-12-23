from core.config import get_config
from core.config.loader import ConfigLoader
from core.config.models import HotspotConfig


def get_hotspot_config() -> HotspotConfig:
    raw, version = get_config()
    data = ConfigLoader(raw, version).hotspot()
    return data


config = get_hotspot_config()
ONLINE_TIMEOUT = config.online_timeout
