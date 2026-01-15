import bcrypt
from sqlalchemy import select

from core.database.models.admin_users import AdminUsers
from core.database.session import get_session


ACCESS_LEVELS = {
    "none": 0,
    "read": 1,
    "write": 2,
    "admin": 3,
}


def check_password(username: str, password: str):
    with get_session() as db_session:
        query = select(AdminUsers).where(username==username)
        user = db_session.scalars(query).first()

        if not user:
            return False
        
        if not user.password_hash:
            return False
        
        return bcrypt.checkpw(password.encode('utf-8'), user.password_hash)


def has_access(username: str, section: str, level: str) -> bool:
     with get_session() as db_session:
        query = select(AdminUsers).where(username==username)
        user = db_session.scalars(query).first()
        user_level = user.access.get(section, "none")
        return ACCESS_LEVELS[user_level] >= ACCESS_LEVELS[level]
