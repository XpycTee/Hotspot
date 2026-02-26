from hashlib import sha256

from sqlalchemy import select

from core.database.models.wifi_client import WifiClient
from core.database.session import get_session


def hash_fingerprint(phone_number, hardware_fp):
    fingerprint_source = hardware_fp or "no-hardware-fp"
    return sha256(f"{fingerprint_source}:{phone_number}".encode()).hexdigest()


def update_fingerprint(mac, user_fp):
    with get_session() as db_session:
        query = select(WifiClient).where(WifiClient.mac==mac)
        wifi_client = db_session.scalars(query).first()
        wifi_client.user_fp = user_fp
        db_session.commit()
