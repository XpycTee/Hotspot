from sqlalchemy import select

from core.db.models.employee_phone import EmployeePhone
from core.db.models.wifi_client import WifiClient
from core.db.session import SessionLocal
from core.wifi.client import find_by_mac


def check_employee(phone_number) -> bool:
    session = SessionLocal()
    query = select(EmployeePhone).where(EmployeePhone.phone_number==phone_number)
    employee_phone = session.scalars(query).first()
    return employee_phone is not None


def update_status(wifi_client: WifiClient, new_status: bool):
    session = SessionLocal()
    wifi_client.employee = new_status
    session.commit()


def update_status_by_mac(mac: str, new_status: bool):
    wifi_client = find_by_mac(mac)
    return update_status(wifi_client, new_status)
