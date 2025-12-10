from environs import Env

from core.config import SETTINGS

env = Env(prefix='HOTSPOT_DB_')
env.read_env()

DEFAULT_DB_URL = 'sqlite:///hotspot.db'

DB_URL = env.str('URL', SETTINGS.get('db_url', DEFAULT_DB_URL))

