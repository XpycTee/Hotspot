from sqlalchemy import Column, String

from core.database.models import Model


class Blacklist(Model):
    __tablename__ = "blacklist"

    phone_number = Column(String(20), primary_key=True)