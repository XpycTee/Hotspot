from core.db.models.blacklist import Blacklist
from core.db.models.employee_phone import EmployeePhone
from core.db.models.wifi_client import WifiClient
from core.db.session import get_session


from sqlalchemy import select


def check_employee(phone_number) -> bool:
    session = get_session()
    query = select(EmployeePhone).where(EmployeePhone.phone_number==phone_number)
    employee_phone = session.scalars(query).first()
    return employee_phone is not None


def update_status(wifi_client: WifiClient, new_status: bool):
    session = get_session()
    wifi_client.employee = new_status
    session.commit()


def check_blacklist(phone_number) -> bool:
    session = get_session()
    query = select(Blacklist).where(Blacklist.phone_number==phone_number)
    blocked_client = session.scalars(query).first()
    return blocked_client