from sqlalchemy import Column, ForeignKey, Integer, String

from core.db.models import Model


class EmployeePhone(Model):
    __tablename__ = "employee_phone"

    phone_number = Column(String(20), primary_key=True)
    employee_id = Column(Integer, ForeignKey('employee.id'), nullable=False)