from dataclasses import dataclass, field
from typing import Dict, List, Mapping


@dataclass(frozen=True)
class RadiusPortsConfig:
    """
    RADIUS service ports configuration.
    """

    auth: int = 1812
    acct: int = 1813
    coa: int = 3799


@dataclass(frozen=True)
class RemoteHost:
    """Remote RADIUS capable host we can talk to.

    Args:
        address (str): IP address.
        secret (bytes): RADIUS secret. If connecting to a RadSec server, the secret should be `radsec`.
        name (str): Short name (used for logging only).
        authport (int): Port used for authentication packets.
        acctport (int): Port used for accounting packets.
        coaport (int): Port used for CoA packets.
        enabled (bool): Status enabling of host.
    """
    
    address: str
    secret: bytes
    name: str
    authport: int = 1812
    acctport: int = 1813
    coaport: int = 3799
    enabled: bool = True


@dataclass
class RadiusConfig:
    """
    RADIUS server configuration.
    """

    enabled: bool = True
    addresses: List[str] = field(default_factory=list)
    ports: RadiusPortsConfig = field(default_factory=RadiusPortsConfig)
    hosts: Mapping[str, RemoteHost] = field(default_factory=RemoteHost)