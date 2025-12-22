from dataclasses import dataclass, field
from typing import List, Optional
from environs import Env
import yaml

from core.config import SETTINGS

env = Env()
env.read_env()


@dataclass
class RadiusPortsConfig:
    auth: int = 1812
    acct: int = 1813
    CoA: int = 3799


@dataclass
class RadiusConfig:
    addresses: List[str] = field(default_factory=list)
    ports: RadiusPortsConfig = field(default_factory=RadiusPortsConfig)
    hosts: Optional[dict] = None  # импортируемый YAML (hosts.yaml)


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


RADIUS = RadiusConfig(
    enabled=RADIUS_ENABLED,
    addresses=radius_addresses, 
    ports=RadiusPortsConfig(
        auth=radius_auth_port,
        acct=radius_acct_port,
        CoA=radius_coa_port
    ),
    hosts=radius_hosts
)
