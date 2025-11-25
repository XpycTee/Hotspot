import datetime

from sqlalchemy import select

from core.db.models.wifi_client import WifiClient
from core.db.session import get_session
from core.wifi.repository import find_by_mac


def _get_today() -> datetime.datetime:
    return datetime.datetime.combine(
        datetime.date.today(),
        datetime.time(6, 0)
    )


def update_expiration(mac, user_delay: datetime.timedelta):
    today_start = _get_today()

    with get_session() as db_session:
        
        expire_time = today_start + user_delay
        if expire_time < datetime.datetime.now():
            expire_time += datetime.timedelta(days=1)
            
        query = select(WifiClient).where(WifiClient.mac==mac)
        wifi_client = db_session.scalars(query).first()
        wifi_client.expiration = expire_time
        db_session.commit()
        
