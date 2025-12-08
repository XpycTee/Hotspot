from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String

from sqlalchemy.orm import relationship

from core.database.models import Model
from core.database.models.clients_number import ClientsNumber


class WifiClient(Model):
    __tablename__ = "wifi_client"

    id = Column(Integer, primary_key=True)
    mac = Column(String(17), unique=True)
    user_fp =  Column(String(64))
    expiration = Column(DateTime)
    employee = Column(Boolean)
    phone_id = Column(Integer, ForeignKey(ClientsNumber.id))
    phone = relationship(ClientsNumber, backref='phones')
    online = Column(Boolean)
    last_location = Column(String(64))
    last_ipv4_address = Column(String(15))