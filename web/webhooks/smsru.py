import hashlib
from flask import Blueprint, Response, request

from core.config import get_config
from core.redis import cache


smsru_bp = Blueprint('smsru', __name__, url_prefix='/smsru')


@smsru_bp.route('', methods=['POST'])
def index():
    post = request.form

    indexed_data: dict[int, str] = {}
    received_hash = post.get('hash')

    config = get_config()
    api_key = config.sender.api_key

    for key, value in post.items():
        if key.startswith('data'):
            index = int(key[5:-1])
            indexed_data[index] = value

    if not indexed_data:
        return Response("data missing", status=400)

    if not received_hash:
        return Response("hash missing", status=400)

    data = [indexed_data[i] for i in sorted(indexed_data)]

    concat_data = "".join(data)

    calculated_hash = hashlib.sha256(
        (api_key + concat_data).encode("utf-8")
    ).hexdigest()

    if calculated_hash != received_hash:
        return Response("invalid hash", status=403)

    for entry in data:
        lines = entry.split("\n")

        if lines[0] == "callcheck_status":
            data = {
                'check_id': lines[1],
                'check_status': int(lines[2]),
                'unix_timestamp': float(lines[3]),
            }
            check_id = lines[1]
            cache.set(f'callcheck:smsru:confirm:{check_id}', data, 120)

    return Response("100", status=200)
