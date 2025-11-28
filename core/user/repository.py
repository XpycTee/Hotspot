import datetime

from core.logging.logger import logger
from sqlalchemy.exc import IntegrityError
from core.database.models.blacklist import Blacklist
from core.database.models.clients_number import ClientsNumber
from core.database.models.employee_phone import EmployeePhone
from core.database.models.wifi_client import WifiClient
from core.database.session import get_session


from sqlalchemy import select


def check_employee(phone_number) -> bool:
    with get_session() as db_session:
        query = select(EmployeePhone).where(EmployeePhone.phone_number==phone_number)
        employee_phone = db_session.scalars(query).first()
        return employee_phone is not None


def update_status(mac, new_status: bool):
    with get_session() as db_session:
        query = select(WifiClient).where(WifiClient.mac==mac)
        wifi_client = db_session.scalars(query).first()
        wifi_client.employee = new_status
        db_session.commit()


def check_blacklist(phone_number) -> bool:
    with get_session() as db_session:
        query = select(Blacklist).where(Blacklist.phone_number==phone_number)
        blocked_client = db_session.scalars(query).first()
        return blocked_client


def get_or_create_client_phone(phone_number):
    """Получить или создать запись клиента по номеру телефона."""
    with get_session() as db_session:
        now_time = datetime.datetime.now()
        query = select(ClientsNumber).where(ClientsNumber.phone_number==phone_number)
        db_phone = db_session.scalars(query).first()
        if not db_phone:
            try:
                db_phone = ClientsNumber(phone_number=phone_number, last_seen=now_time)
                db_session.add(db_phone)
                db_session.commit()
                logger.debug(f"Create new number {phone_number} by time {now_time}")
            except IntegrityError:
                db_session.rollback()
                db_phone = db_session.scalars(query).first()
        return db_phone

def update_last_seen(phone_number):
    now_time = datetime.datetime.now()
    db_phone = get_or_create_client_phone(phone_number)
    with get_session() as db_session:
        try:
            db_phone.last_seen = now_time
            db_session.commit()
            logger.debug(f"Update time {now_time} for number {phone_number}")
        except IntegrityError:
            db_session.rollback()
            logger.error(f"Failed to update last_seen for phone number: {phone_number}")