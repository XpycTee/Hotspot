from core.config.admin import ADMIN


import bcrypt


def check_password(username, password):
    stored_username = ADMIN.get('username')
    stored_password_hash = ADMIN.get('password')

    if not stored_password_hash:
        return False
    if not stored_username:
        return False

    return stored_username == username and bcrypt.checkpw(password.encode('utf-8'), stored_password_hash.encode('utf-8'))
