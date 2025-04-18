from sqlalchemy import Column, ForeignKey
from sqlalchemy.types import Boolean, Integer, String, DateTime

from app.database import db


class ClientsNumber(db.Model):
    id = Column(Integer, primary_key=True)
    phone_number = Column(String(20))
    last_seen = Column(DateTime)


class WifiClient(db.Model):
    id = Column(Integer, primary_key=True)
    mac = Column(String(17))
    expiration = Column(DateTime)
    employee = Column(Boolean)
    phone_id = Column(Integer, ForeignKey(ClientsNumber.id))
    phone = db.relationship(ClientsNumber, backref='phones')


class Employee(db.Model):
    id = Column(Integer, primary_key=True)
    lastname = Column(String(50), nullable=False)
    name = Column(String(50), nullable=False)
    phones = db.relationship('EmployeePhone', backref='employee')


class EmployeePhone(db.Model):
    phone_number = Column(String(20), primary_key=True)
    employee_id = Column(Integer, ForeignKey('employee.id'), nullable=False)


class Blacklist(db.Model):
    phone_number = Column(String(20), primary_key=True)
