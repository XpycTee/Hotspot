from dataclasses import asdict

from pyrad2 import server

from core.config import CONFIG
from core.config.store import ConfigStore


def get_radius_hosts():
    hosts = {}
    for host, data in RADIUS.hosts.items():
        return_data = asdict(data)
        del return_data['secret']
        hosts[host] = return_data
    return hosts


def add_radius_host(data: dict):
    secret = data.get('secret')
    if secret is not None:
        data['secret'] = secret.encode()

    RADIUS.hosts[data['address']] = server.RemoteHost(**data)

    store = ConfigStore()
    store.save()

    return {'status': 'OK'}


def update_radius_host(host: str, data: dict):
    update_host = RADIUS.hosts.pop(host)
    
    for key, value in data.items():
        if key == 'secret':
            value = value.encode()
        if key == 'address' and value != host:
            host = value
        update_host.__dict__[key] = value

    RADIUS.hosts[host] = update_host

    store = ConfigStore()
    store.save()
    
    return {'status': 'OK'}


def delete_radius_host(host: str):
    del RADIUS.hosts[host]

    store = ConfigStore()
    store.save()

    return {'status': 'OK'}
