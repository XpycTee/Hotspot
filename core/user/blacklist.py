from sqlalchemy import select

from core.db.models.blacklist import Blacklist
from core.db.session import SessionLocal


def check_blacklist(phone_number) -> bool:
    session = SessionLocal()
    query = select(Blacklist).where(Blacklist.phone_number==phone_number)
    blocked_client = session.scalars(query).first()
    return blocked_client
