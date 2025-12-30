from dataclasses import asdict

from core.config.models import RemoteHost
from core.config.store import ConfigLoader


def get_radius_hosts():
    config = ConfigLoader().load()
    hosts = {}
    for host, data in config.radius.hosts.items():
        return_data = asdict(data)
        del return_data['secret']
        hosts[host] = return_data
    return hosts


def add_radius_host(address: str, secret: bytes, name: str,
        authport: int, acctport: int, coaport: int):

    with ConfigLoader().update() as config:
        config.radius.hosts[address] = RemoteHost(
            address=address,
            secret=secret,
            name=name,
            authport=authport,
            acctport=acctport,
            coaport=coaport
        )

    return {'status': 'OK'}


def update_radius_host(host: str, 
        address: str, secret: bytes, name: str,
        authport: int, acctport: int, coaport: int):

    with ConfigLoader().update() as config:
        hosts = config.radius.hosts

        orig_host = hosts.pop(host)
        
        new_host = address if address != host else host
        if not secret:
            secret = orig_host.secret

        hosts[new_host] = RemoteHost(
            address=address,
            secret=secret,
            name=name,
            authport=authport,
            acctport=acctport,
            coaport=coaport
        )
    
    return {'status': 'OK'}


def delete_radius_host(host: str):

    with ConfigLoader().update() as config:
        _ = config.radius.hosts.pop(host)

    return {'status': 'OK'}
