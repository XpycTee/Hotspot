from sqlalchemy import select
from core.database.models.admin_users import AdminUsers
from core.database.session import get_session

ACCESS_GROUPS = {
    "none": 0,
    "read": 1,
    "write": 2,
    "full": 3,
}


def is_valid_group(group: str | None) -> bool:
    return group in ACCESS_GROUPS


def has_access(username: str, group: str) -> bool:
    required_level = ACCESS_GROUPS.get(group)
    if required_level is None:
        return False

    with get_session() as db_session:
        query = select(AdminUsers).where(AdminUsers.username==username)
        user = db_session.scalars(query).first()
        if not user:
            return False

        user_level = ACCESS_GROUPS.get(user.group)
        if user_level is None:
            return False

        return user_level >= required_level
