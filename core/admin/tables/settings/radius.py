from dataclasses import asdict

from core.config.models import RemoteHost
from core.config.store import ConfigStore


def get_radius_hosts():
    config = ConfigStore().load()
    hosts = {}
    for host, data in config.radius.hosts_data.items():
        return_data = asdict(data)
        del return_data['secret']
        hosts[host] = return_data
    return hosts


def add_radius_host(address: str, secret: bytes, name: str,
        authport: int, acctport: int, coaport: int):

    with ConfigStore().update() as config:
        config.radius.hosts_data[address] = RemoteHost(
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

    with ConfigStore().update() as config:
        hosts = config.radius.hosts_data

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

    with ConfigStore().update() as config:
        _ = config.radius.hosts_data.pop(host)

    return {'status': 'OK'}
