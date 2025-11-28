from environs import Env

env = Env(prefix="HOTSPOT_DB_")
env.read_env()


DB_URL = env.str("URL", default='sqlite:///config/hotspot.db')
