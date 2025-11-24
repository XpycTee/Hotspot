from sqlalchemy import select
from core.db.models.wifi_client import WifiClient
from core.db.session import SessionLocal


def find_by_mac(mac):
    session = SessionLocal()
    query = select(WifiClient).where(WifiClient.mac==mac)
    wifi_client = session.scalars(query).first()
    return wifi_client


def find_by_fp(user_fp):
    session = SessionLocal()
    query = select(WifiClient).where(WifiClient.user_fp==user_fp)
    wifi_client = session.scalars(query).first()
    return wifi_client
