from environs import Env

env = Env(prefix="HOTSPOT_RADIUS_")
env.read_env()

RADIUS_ENABLED = env.bool('ENABLED', False)

RADIUS_HOST = env.str('HOST', '0.0.0.0')
RADIUS_PORT = env.int('PORT', 1812)

RADIUS_CLIENT = env.str('CLIENT', None)

secret = env.str('SECRET', None)
if isinstance(secret, str):
    secret = secret.encode()
    
RADIUS_SECRET = secret
