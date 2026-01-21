from sqlalchemy import select
from core.database.models.admin_users import AdminUsers
from core.database.session import get_session
from core.utils.password import hashpw


def create_user(username: str, password: str, group: str, access: dict | None = None):
    with get_session() as db_session:        
        query = select(AdminUsers).where(AdminUsers.username==username)
        db_user = db_session.scalars(query).first()

        if not db_user:
            password_hash = hashpw(password)
            if not access:
                access = {}

            new_user = AdminUsers(
                username=username, 
                password_hash=password_hash,
                group=group,
                access=access,
            )
            db_session.add(new_user)
            return {'status': 'OK'}
        return {'status': 'ALREADY'}


def get_user(username: str):
    with get_session() as db_session:        
        query = select(AdminUsers).where(AdminUsers.username==username)
        db_user = db_session.scalars(query).first()
        if not db_user:
            return {'status': 'NOT_FOUND'}

        user = {
            'username': db_user.username,
            'access': db_user.access,
        }
        return {
            'status': 'OK', 
            'user': user,
        }


def delete_user(username: str):
     with get_session() as db_session:        
        query = select(AdminUsers).where(AdminUsers.username==username)
        db_user = db_session.scalars(query).first()
        if not db_user:
            return {'status': 'NOT_FOUND'}
        
        user = {
            'username': db_user.username,
            'access': db_user.access,
        }
        db_session.delete(db_user)

        return {
            'status': 'OK', 
            'user': user,
        }


def update_user(username: str, password: str | None = None, access: dict | None = None):
    with get_session() as db_session:        
        query = select(AdminUsers).where(AdminUsers.username==username)
        db_user = db_session.scalars(query).first()
        if not db_user:
            return {'status': 'NOT_FOUND'}
        
        if password:
            password_hash = hashpw(password)
            db_user.password_hash = password_hash
        
        if access:
            db_user.access = access

        return {'status': 'OK'}