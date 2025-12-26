import bcrypt

from core.config import CONFIG


def check_password(username: str, password: str):
    admin = CONFIG.admin
    stored_username = admin.username
    stored_password_hash = admin.password_hash

    if not stored_password_hash:
        return False
    if not stored_username:
        return False

    return stored_username == username and bcrypt.checkpw(password.encode('utf-8'), stored_password_hash)
