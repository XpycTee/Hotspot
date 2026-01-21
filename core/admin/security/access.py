from sqlalchemy import select
from core.database.models.admin_users import AdminUsers
from core.database.session import get_session

ACCESS_GROUPS = {
    "none": 0,
    "read": 1,
    "write": 2,
    "full": 3,
}


def has_access(username: str, group: str) -> bool:
     with get_session() as db_session:
        query = select(AdminUsers).where(AdminUsers.username==username)
        user = db_session.scalars(query).first()

        return ACCESS_GROUPS[user.group] >= ACCESS_GROUPS[group]
