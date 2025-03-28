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
