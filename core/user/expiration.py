import datetime

from sqlalchemy import select

from core.db.models.wifi_client import WifiClient
from core.db.session import get_session


def get_delay(is_employee: bool) -> datetime.timedelta:
    # TODO
    return datetime.timedelta(minutes=(10 if is_employee else 5))

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
