import bcrypt

from core.config import get_config


def check_password(username: str, password: str):
    config = get_config()
    stored_username = config.admin.username
    stored_password_hash = config.admin.password_hash

    if not stored_password_hash:
        return False
    if not stored_username:
        return False

    return stored_username == username and bcrypt.checkpw(password.encode('utf-8'), stored_password_hash)
