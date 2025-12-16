from core.config import SETTINGS


def get_settings(name):
    if name == 'radius':
        hosts = SETTINGS['radius'].get('hosts')
        return hosts
    

def update_settings(setting, data):
    return {'status': 'OK'}


def radius_delete_host(data):
    return {'status': 'OK'}