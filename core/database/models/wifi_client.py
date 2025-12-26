from datetime import datetime
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String

from sqlalchemy.orm import relationship

from core.database.models import Model
from core.database.models.clients_number import ClientsNumber
from core.database.models.employee import Employee


class WifiClient(Model):
    __tablename__ = "wifi_client"

    id = Column(Integer, primary_key=True)
    mac = Column(String(17), unique=True)
    user_fp =  Column(String(64))
    expiration = Column(DateTime)

    employee_id = Column(Integer, ForeignKey(Employee.id))
    employee = relationship(Employee, backref='wifi_client')

    phone_id = Column(Integer, ForeignKey(ClientsNumber.id))
    phone = relationship(ClientsNumber, backref='wifi_client')

    last_seen = Column(DateTime)
    last_location = Column(String(64))
    last_ipv4_address = Column(String(15))

    @property
    def online(self) -> bool:
        from core.config.hotspot import HOTSPOT
        return self.last_seen and (datetime.now() - self.last_seen) < HOTSPOT.online_timeout

    @property
    def is_employee(self) -> bool:
        return self.employee_id is not None
    
    @property
    def phone_number(self) -> str:
        return self.phone.phone_number if self.phone else None
    