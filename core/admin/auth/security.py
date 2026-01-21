import bcrypt
from sqlalchemy import select

from core.database.models.admin_users import AdminUsers
from core.database.session import get_session



def check_password(username: str, password: str):
    with get_session() as db_session:
        query = select(AdminUsers).where(AdminUsers.username==username)
        user = db_session.scalars(query).first()

        if not user:
            return False
        
        if not user.password_hash:
            return False
        
        return bcrypt.checkpw(password.encode('utf-8'), user.password_hash)
    


