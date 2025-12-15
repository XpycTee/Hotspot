from core.config import SETTINGS


def get_settings(search_query):
    radius_settings = SETTINGS.get('radius')
    return {'radius': radius_settings}