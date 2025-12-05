import datetime
from environs import Env

env = Env(prefix="HOTSPOT_USERS_")
env.read_env()

def convert_delay(delay):
    suffixes = {
        'w': 'weeks',
        'd': 'days',
        'h': 'hours',
        'm': 'minutes',
        's': 'seconds'
    }

    amount, suffix = (int(delay[:-1]), delay[-1]) if delay[-1] in suffixes else (int(delay), 'h')
    return datetime.timedelta(**{suffixes[suffix]: amount})

with env.prefixed("STAFF_"):
    STAFF_USER: dict = {'password': env.str("PASS", 'supersecret'), 'delay': convert_delay(env.str("DELAY", '30d'))}

with env.prefixed("GUEST_"):
    GUEST_USER: dict = {'password': env.str("PASS", 'secret'), 'delay': convert_delay(env.str("DELAY", '1d'))}
