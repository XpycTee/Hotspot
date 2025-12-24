from core.admin.tables.settings.radius import get_radius_hosts


def get_settings(name):
    if name == 'radius':
        return get_radius_hosts()


def update_settings(setting, data: dict):
    if setting == 'radius':
        pass
    return {'status': 'OK'}