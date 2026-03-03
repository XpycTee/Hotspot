from sqlalchemy.exc import IntegrityError
from core.database.models.wifi_client import WifiClient
from core.database.session import get_session


from sqlalchemy import distinct, select

from core.hotspot.user.employees import get_employee
from core.hotspot.user.expiration import new_expiration
from core.hotspot.user.repository import get_or_create_clients_number


def find_by_mac(mac):
    with get_session() as db_session:
        query = select(WifiClient).where(WifiClient.mac==mac)
        wifi_client = db_session.scalars(query).first()
        if not wifi_client:
            return None
            
        return {
            "mac": wifi_client.mac,
            "expiration": wifi_client.expiration,
            "is_employee": wifi_client.is_employee,
            "phone": wifi_client.phone_number,
            "user_fp": wifi_client.user_fp,
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
            "is_employee": wifi_client.is_employee,
            "phone": wifi_client.phone_number,
            "user_fp": wifi_client.user_fp,
        }


def update_wifi_client(mac, phone_number, user_fp):
    """Создать запись WiFi клиента по MAC-адресу, если нету."""
    db_phone = get_or_create_clients_number(phone_number)
    db_employee = get_employee(phone_number)
    expiration = new_expiration(db_employee is not None)
    with get_session() as db_session:
        query = select(WifiClient).where(WifiClient.mac==mac)
        db_client = db_session.scalars(query).first()
        if not db_client:
            raise RuntimeError("DB Error: wifi client not found")

        db_client.expiration = expiration
        db_client.employee = db_employee
        db_client.phone = db_phone
        db_client.user_fp = user_fp
        db_session.commit()


def create_wifi_client(mac, phone_number, user_fp):
    """Создать запись WiFi клиента по MAC-адресу."""
    db_phone = get_or_create_clients_number(phone_number)
    db_employee = get_employee(phone_number)
    expiration = new_expiration(db_employee is not None)
    with get_session() as db_session:
        db_client = WifiClient(mac=mac, expiration=expiration, employee=db_employee, phone=db_phone, user_fp=user_fp)
        db_session.add(db_client)
        db_session.commit()


def get_locations():
    with get_session() as db_session:
        query = distinct(WifiClient.last_location)
        locations = db_session.query(query).order_by(WifiClient.last_location.asc()).all()
        list_locations = [v[0] for v in locations]
        return list_locations
    
    
def update_mac(old, new):
    with get_session() as db_session:
        query = select(WifiClient).where(WifiClient.mac==old)
        wifi_client = db_session.scalars(query).first()
        wifi_client.mac = new
        db_session.commit()
