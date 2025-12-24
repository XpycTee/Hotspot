import dataclasses

from pyrad2 import server

from core.config.radius import RADIUS
from core.redis.config import ConfigStore


def get_radius_hosts():
    hosts = {}
    for host, data in RADIUS.hosts.items():
        return_data = dataclasses.asdict(data)
        del return_data['secret']
        hosts[host] = return_data
    return hosts


def add_radius_host(data: dict):
    RADIUS.hosts[data['address']] = server.RemoteHost(**data)
    RADIUS.version += 1

    store = ConfigStore('radius')
    store.save(RADIUS)

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

    RADIUS.version += 1

    store = ConfigStore('radius')
    store.save(RADIUS)
    
    return {'status': 'OK'}


def delete_radius_host(host: str):
    del RADIUS.hosts[host]
    RADIUS.version += 1

    store = ConfigStore('radius')
    store.save(RADIUS)

    return {'status': 'OK'}
