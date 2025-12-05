import datetime

from core.logging.logger import logger
from sqlalchemy.exc import IntegrityError
from core.database.models.clients_number import ClientsNumber
from core.database.session import get_session


from sqlalchemy import select


def get_or_create_clients_number(phone_number):
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


def update_clients_numbers_last_seen(phone_number):
    now_time = datetime.datetime.now()
    db_phone = get_or_create_clients_number(phone_number)
    with get_session() as db_session:
        try:
            db_phone.last_seen = now_time
            db_session.commit()
            logger.debug(f"Update time {now_time} for number {phone_number}")
        except IntegrityError:
            db_session.rollback()
            logger.error(f"Failed to update last_seen for phone number: {phone_number}")
