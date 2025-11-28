from sqlalchemy import Column, Integer, String

from sqlalchemy.orm import relationship

from core.database.models import Model
from core.database.models.employee_phone import EmployeePhone


class Employee(Model):
    __tablename__ = "employee"
    
    id = Column(Integer, primary_key=True)
    lastname = Column(String(50), nullable=False)
    name = Column(String(50), nullable=False)
    phones = relationship(EmployeePhone, backref='employee')