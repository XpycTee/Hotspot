from sqlalchemy import Column, DateTime, Integer, String

from core.database.models import Model


class ClientsNumber(Model):
    __tablename__ = "clients_number"

    id = Column(Integer, primary_key=True)
    phone_number = Column(String(20), unique=True)
    last_seen = Column(DateTime)