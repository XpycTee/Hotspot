from hashlib import sha256


def get_fingerprint(phone_number, hardware_fp):
    user_fp = None
    if hardware_fp:
        user_fp = sha256(f"{hardware_fp}:{phone_number}".encode()).hexdigest()
    return user_fp
