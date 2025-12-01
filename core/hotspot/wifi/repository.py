from sqlalchemy.exc import IntegrityError
from core.database.models.wifi_client import WifiClient
from core.database.session import get_session


from sqlalchemy import select

from core.hotspot.user.expiration import new_expiration
from core.hotspot.user.repository import get_or_create_client_phone


def find_by_mac(mac):
    with get_session() as db_session:
        query = select(WifiClient).where(WifiClient.mac==mac)
        wifi_client = db_session.scalars(query).first()
        if not wifi_client:
            return None
            
        return {
            "mac": wifi_client.mac,
            "expiration": wifi_client.expiration,
            "employee": wifi_client.employee,
            "phone": wifi_client.phone.phone_number if wifi_client.phone else None
        }


def find_by_fp(user_fp):
    with get_session() as db_session:
        query = select(WifiClient).where(WifiClient.user_fp==user_fp)
        wifi_client = db_session.scalars(query).first()
        if not wifi_client:
            return None
            
        return {
            "mac": wifi_client.mac,
            "expiration": wifi_client.expiration,
            "employee": wifi_client.employee,
            "phone": wifi_client.phone.phone_number if wifi_client.phone else None
        }


def create_or_udpate_wifi_client(mac, is_employee, phone_number):
    """Создать запись WiFi клиента по MAC-адресу, если нету."""
    db_phone = get_or_create_client_phone(phone_number)
    expiration = new_expiration(is_employee)
    with get_session() as db_session:
        query = select(WifiClient).where(WifiClient.mac==mac)
        db_client = db_session.scalars(query).first()

        if not db_client:
            try:
                db_client = WifiClient(mac=mac, expiration=expiration, employee=is_employee, phone=db_phone, user_fp=None)
                db_session.add(db_client)
                db_session.commit()
            except IntegrityError:
                db_session.rollback()
        else:
            try:
                db_client.expiration = expiration
                db_client.employee = is_employee
                db_client.phone = db_phone
                db_session.commit()
            except IntegrityError:
                db_session.rollback()
