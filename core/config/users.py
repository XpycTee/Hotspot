from dataclasses import dataclass
from datetime import timedelta
from environs import Env

from core.config import SETTINGS, convert_delay

env = Env(prefix='HOTSPOT_USERS_')
env.read_env()


@dataclass
class HotspotUserConfig:
    password: str
    delay: timedelta


hotspot = SETTINGS.get('hotspot', {})
users = SETTINGS.get('users', {})

with env.prefixed('STAFF_'):
    staff_user = users.get('staff', {})
    STAFF_USER = HotspotUserConfig(
        password=env.str('PASS', staff_user.get('password', 'supersecret')), 
        delay=convert_delay(env.str('DELAY', staff_user.get('delay', '30d')))
    )

with env.prefixed('GUEST_'):
    guest_user = users.get('guest', {})
    GUEST_USER = HotspotUserConfig(
        password=env.str('PASS', guest_user.get('password', 'secret')), 
        delay=convert_delay(env.str('DELAY', guest_user.get('delay', '1d')))
    )
