import datetime

from sqlalchemy import select

from core.config.users import GUEST_USER, STAFF_USER
from core.database.models.wifi_client import WifiClient
from core.database.session import get_session


def get_delay(is_employee: bool) -> datetime.timedelta:
    if is_employee:
        delay = STAFF_USER.get('delay')
    else:
        delay = GUEST_USER.get('delay')
    return delay

def new_expiration(is_employee: bool):
    today_start = datetime.datetime.combine(
        datetime.date.today(),
        datetime.time(6, 0)
    )
    user_delay = get_delay(is_employee)
    expire_time = today_start + user_delay
    if expire_time < datetime.datetime.now():
        expire_time += datetime.timedelta(days=1)
    return expire_time

def update_expiration(mac):
    with get_session() as db_session:
        query = select(WifiClient).where(WifiClient.mac==mac)
        wifi_client = db_session.scalars(query).first()
        wifi_client.expiration = new_expiration(wifi_client.employee)
        db_session.commit()

def reset_expiration(mac):
    with get_session() as db_session:
        query = select(WifiClient).where(WifiClient.mac==mac)
        wifi_client = db_session.scalars(query).first()
        wifi_client.expiration = datetime(1970, 1, 1)
        db_session.commit()
