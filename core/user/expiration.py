import datetime

from core.db.models.wifi_client import WifiClient
from core.db.session import SessionLocal
from core.wifi.client import find_by_mac


def _get_today() -> datetime.datetime:
    return datetime.datetime.combine(
        datetime.date.today(),
        datetime.time(6, 0)
    )


def update_expiration(wifi_client: WifiClient, user_delay: datetime.timedelta):
    session = SessionLocal()
    today_start = _get_today()

    expire_time = today_start + user_delay
    if expire_time < datetime.datetime.now():
        expire_time += datetime.timedelta(days=1)

    wifi_client.expiration = expire_time
    session.commit()


def update_expiration_by_mac(mac: str, user_delay: datetime.timedelta):
    wifi_client = find_by_mac(mac)
    return update_expiration(wifi_client, user_delay)