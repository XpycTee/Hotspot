from core.config.admin import ADMIN


import bcrypt


def check_password(username: str, password: str):
    stored_username = ADMIN.username
    stored_password_hash = ADMIN.password

    if not stored_password_hash:
        return False
    if not stored_username:
        return False

    return stored_username == username and bcrypt.checkpw(password.encode('utf-8'), stored_password_hash)
