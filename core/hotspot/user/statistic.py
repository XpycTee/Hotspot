from datetime import datetime
from sqlalchemy import select

from core.database.models.wifi_client import WifiClient
from core.database.session import get_session


def update_statistic(mac: str, alive: bool, location: str, ip_address: str):
    with get_session() as db_session:
        query = select(WifiClient).where(WifiClient.mac==mac)
        wifi_client = db_session.scalars(query).first()

        if not wifi_client:
            return {'status': 'NOT_FOUND'}
        
        if alive:
            wifi_client.last_seen = datetime.now()
        wifi_client.last_location = location
        wifi_client.last_ipv4_address = ip_address
    
    return {'status': 'OK'}