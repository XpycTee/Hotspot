from environs import Env

env = Env(prefix="HOTSPOT_RADIUS_")
env.read_env()

RADIUS_ENABLED = env.bool('ENABLED', False)

RADIUS_ADDRESSES = env.list('ADDRESSES', ['::'])
RADIUS_AUTH_PORT = env.int('AUTH_PORT', 1812)
RADIUS_ACCT_PORT = env.int('ACCT_PORT', 1813)
RADIUS_COA_PORT = env.int('COA_PORT', 3799)

def configure_clients():
    return [{
        'name': 'all',
        'host': '0.0.0.0',
        'secret': b'Kah3choteereethiejeimaeziecumi'
    }]

RADIUS_CLIENTS = configure_clients()
