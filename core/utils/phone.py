import re


def normalize_phone(phone_number: str) -> str:
    """Normalize phone to digits, leading 7 for Russia-style numbers."""
    if not phone_number:
        return ''
    num = re.sub(r'\D', '', phone_number)
    num = re.sub(r'^8', '7', num)
    if num.startswith('07'):  # guard: if weird leading zero
        num = '7' + num[2:]
    return num
