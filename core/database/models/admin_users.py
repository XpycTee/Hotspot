from sqlalchemy import JSON, Column, Integer, LargeBinary, String
from core.database.models import Model


class AdminUsers(Model):
    __tablename__ = "admin_users"

    id = Column(Integer, primary_key=True)
    username = Column(String(16), nullable=False)
    password_hash = Column(LargeBinary(128), nullable=False)
    group = Column(String(8), nullable=False)
    access = Column(JSON, nullable=False, default=dict)
