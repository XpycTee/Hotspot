from environs import Env

from core.config import SETTINGS, convert_delay

env = Env(prefix='HOTSPOT_USERS_')
env.read_env()

users = SETTINGS.get('hotspot_users', {})

with env.prefixed('STAFF_'):
    staff_user = users.get('staff', {})
    STAFF_USER: dict = {
        'password': env.str('PASS', staff_user.get('password', 'supersecret')), 
        'delay': convert_delay(env.str('DELAY', staff_user.get('delay', '30d')))
    }

with env.prefixed('GUEST_'):
    guest_user = users.get('guest', {})
    GUEST_USER: dict = {
        'password': env.str('PASS', guest_user.get('password', 'secret')), 
        'delay': convert_delay(env.str('DELAY', guest_user.get('delay', '1d')))
    }
