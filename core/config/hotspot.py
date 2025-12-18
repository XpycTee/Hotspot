from environs import Env

from core.config import SETTINGS

env = Env(prefix='HOTSPOT_USERS_')
env.read_env()


hotspot = SETTINGS.get('hotspot')

ONLINE_TIMEOUT = env.str('HOTSPOT_ONLINE_TIMEOUT', hotspot.get('online_timeout', 'en'))

