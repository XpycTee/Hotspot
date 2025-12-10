from environs import Env
import yaml

from core.config import SETTINGS

env = Env(prefix='HOTSPOT_RADIUS_')
env.read_env()


radius: dict = SETTINGS.get('radius', {})
ports: dict = radius.get('ports', {})

RADIUS_ENABLED = env.bool('ENABLED', radius.get('enabled', True))
RADIUS_ADDRESSES = env.list('ADDRESSES', radius.get('addresses', ['0.0.0.0']))
RADIUS_AUTH_PORT = env.int('AUTH_PORT', ports.get('auth', 1812))
RADIUS_ACCT_PORT = env.int('ACCT_PORT', ports.get('acct', 1813))
RADIUS_COA_PORT = env.int('COA_PORT', ports.get('CoA', 3799))

def configure_hosts() -> dict:    
    with open('config/hosts.yaml', mode='r') as hosts:
        return yaml.safe_load(hosts)

RADIUS_CLIENTS = radius.get('hosts', configure_hosts())
