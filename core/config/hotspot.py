from environs import Env

from core.config import SETTINGS

env = Env(prefix='HOTSPOT_')
env.read_env()


DEFAULT_ONLINE_TIMEOUT = 300

hotspot = SETTINGS.get('hotspot')
ONLINE_TIMEOUT = env.str('ONLINE_TIMEOUT', hotspot.get('online_timeout', DEFAULT_ONLINE_TIMEOUT))
