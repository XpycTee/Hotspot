from dataclasses import asdict, replace

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
        if not orig_host:
            return {'status': 'FAILED', 'error_message': 'Host not found'}
        
        new_host = address if address != host else host

        updates = {}
        if address:
            updates['address'] = address
        if secret:
            updates['secret'] = secret
        if name:
            updates['name'] = name
        if authport:
            updates['authport'] = authport
        if acctport:
            updates['acctport'] = acctport
        if coaport:
            updates['coaport'] = coaport

        hosts[new_host] = replace(orig_host, **updates)
    
    return {'status': 'OK'}


def delete_radius_host(host: str):

    with ConfigLoader().update() as config:
        try:
            del config.radius.hosts[host]
        except KeyError:
            return {'status': 'FAILED', 'error_message': 'Host not found'}

    return {'status': 'OK'}
