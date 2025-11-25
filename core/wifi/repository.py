from core.db.models.wifi_client import WifiClient
from core.db.session import get_session


from sqlalchemy import select


def find_by_mac(mac):
    session = get_session()
    query = select(WifiClient).where(WifiClient.mac==mac)
    wifi_client = session.scalars(query).first()
    return wifi_client


def find_by_fp(user_fp):
    session = get_session()
    query = select(WifiClient).where(WifiClient.user_fp==user_fp)
    wifi_client = session.scalars(query).first()
    return wifi_client