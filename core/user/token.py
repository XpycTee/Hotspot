import base64


def token_to_hex(raw: bytes):
    return raw.hex()

def token_to_urlsafe(raw: bytes):
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()
