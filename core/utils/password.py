import bcrypt


def hashpw(password: str):
    password_hash = bcrypt.hashpw(
        password.encode(),
        bcrypt.gensalt(),
    )
    return password_hash