import hashlib

def _octal_string_to_bytes(oct_string):
    if not oct_string:
        return b''
    # Split the octal string by backslash and process each part
    byte_nums = []
    for octal_num in oct_string.split("\\")[1:]:
        decimal_value = 0
        # Convert each octal digit to decimal and sum up the values
        for i in range(len(octal_num)):
            decimal_value += int(octal_num[-(i + 1)]) * 8 ** i
        byte_nums.append(decimal_value)
    # Convert the list of decimal values to bytes
    return bytes(byte_nums)


def radius_check_chap(chap_password: bytes, chap_challenge: bytes, password: str):    
    # 1. Извлекаем ID
    chap_id = chap_password[0]

    # 2. Извлекаем хеш
    received_hash = chap_password[1:]   # 16 байт

    # 3. Делаем наш хеш
    m = hashlib.md5()
    m.update(bytes([chap_id]))
    m.update(password.encode("utf-8"))
    m.update(chap_challenge)
    expected_hash = m.digest()

    return received_hash == expected_hash

def hash_chap(chap_id, password, chap_challenge):
    chap_id = _octal_string_to_bytes(chap_id)
    chap_challenge = _octal_string_to_bytes(chap_challenge)
    
    m = hashlib.md5()
    m.update(chap_id)
    m.update(password.encode("utf-8"))
    m.update(chap_challenge)
    hash_chap = m.hexdigest()

    return hash_chap