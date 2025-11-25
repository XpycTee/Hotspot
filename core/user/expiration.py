import datetime

from core.db.models.wifi_client import WifiClient
from core.db.session import get_session
from core.wifi.repository import find_by_mac


def _get_today() -> datetime.datetime:
    return datetime.datetime.combine(
        datetime.date.today(),
        datetime.time(6, 0)
    )


def update_expiration(wifi_client: WifiClient, user_delay: datetime.timedelta):
    session = get_session()
    today_start = _get_today()

    expire_time = today_start + user_delay
    if expire_time < datetime.datetime.now():
        expire_time += datetime.timedelta(days=1)

    wifi_client.expiration = expire_time
    session.commit()
