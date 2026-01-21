from sqlalchemy import select
from core.database.models.admin_users import AdminUsers
from core.database.session import get_session


def get_users():
    users = {}
    with get_session() as db_session:
        query = select(AdminUsers)
        db_users = db_session.scalars(query).all()
        for user in db_users:
            users[user.username] = {
                'username': user.username,
                'access': user.access,
            }
    return users