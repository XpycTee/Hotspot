from sqlalchemy.types import Boolean, Integer, String

from app.database import db


class ClientsNumber(db.Model):
    __tablename__ = 'clients_numbers'

    id = db.Column(Integer, primary_key=True)
    phone_number = db.Column(String)
    last_seen = db.Column(Integer)

    def __repr__(self):
        return f"<ClientsNumber {self.phone_number}>"


class WifiClient(db.Model):
    __tablename__ = 'wifi_clients'

    id = db.Column(Integer, primary_key=True)
    mac = db.Column(String)
    expiration = db.Column(Integer)
    staff = db.Column(Boolean)
    phone_id = db.Column(Integer, db.ForeignKey('clients_numbers.id'))

    def __repr__(self):
        return f"<WifiClient {self.mac}>"
