from environs import Env
import yaml

from core.config import SETTINGS

env = Env()
env.read_env()

with env.prefixed('RADIUS_'):
    RADIUS_ENABLED = env.bool('ENABLED', True)


with env.prefixed('HOTSPOT_RADIUS_'):
    radius: dict = SETTINGS.get('radius', {})
    ports: dict = radius.get('ports', {})

    radius_addresses = env.list('ADDRESSES', radius.get('addresses', ['0.0.0.0']))
    radius_auth_port = env.int('AUTH_PORT', ports.get('auth', 1812))
    radius_acct_port = env.int('ACCT_PORT', ports.get('acct', 1813))
    radius_coa_port = env.int('COA_PORT', ports.get('CoA', 3799))

    def configure_hosts() -> dict:    
        with open('config/hosts.yaml', mode='r') as hosts:
            return yaml.safe_load(hosts)

    radius_hosts = radius.get('hosts', configure_hosts())

SETTINGS['radius'] = {
    'enabled': RADIUS_ENABLED,
    'addresses': radius_addresses, 
    'ports': {
        'auth': radius_auth_port,
        'acct': radius_acct_port,
        'CoA': radius_coa_port
    },
    'hosts': radius_hosts
}
