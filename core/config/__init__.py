import datetime
from environs import Env
import yaml
import yaml_include

env = Env()
env.read_env()


yaml.add_constructor("!import", yaml_include.Constructor(base_dir='config'))

def get_settings() -> dict:
    with open('config/settings.yaml', 'r', encoding='utf-8') as f:
        settings = yaml.full_load(f)
    return settings.get('settings', None)

def convert_delay(delay):
    if isinstance(delay, int):
        return datetime.timedelta(seconds=delay)
    
    suffixes = {
        'w': 'weeks',
        'd': 'days',
        'h': 'hours',
        'm': 'minutes',
        's': 'seconds'
    }

    amount, suffix = (int(delay[:-1]), delay[-1]) if delay[-1] in suffixes else (int(delay), 'h')
    return datetime.timedelta(**{suffixes[suffix]: amount})

SETTINGS = get_settings()


DEBUG: bool = env.bool("DEBUG", SETTINGS.get('debug', False))