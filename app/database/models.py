from sqlalchemy.types import Boolean, Integer, String, DateTime

from app.database import db


class ClientsNumber(db.Model):
    id = db.Column(Integer, primary_key=True)
    phone_number = db.Column(String)
    last_seen = db.Column(DateTime)

    def __repr__(self):
        return f"<ClientsNumber {self.phone_number}>"


class WifiClient(db.Model):
    id = db.Column(Integer, primary_key=True)
    mac = db.Column(String)
    expiration = db.Column(DateTime)
    employee = db.Column(Boolean)
    phone_id = db.Column(Integer, db.ForeignKey(ClientsNumber.id))
    phone = db.relationship(ClientsNumber, backref='phones')

    def __repr__(self):
        return f"<WifiClient {self.mac}>"


class Employee(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    lastname = db.Column(db.String(50), nullable=False)
    name = db.Column(db.String(50), nullable=False)
    phones = db.relationship('EmployeePhone', backref='employee')


class EmployeePhone(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    phone_number = db.Column(db.String(20), nullable=False)
    employee_id = db.Column(db.Integer, db.ForeignKey('employee.id'), nullable=False)


class Blacklist(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    phone = db.Column(db.String(20), unique=True, nullable=False)

