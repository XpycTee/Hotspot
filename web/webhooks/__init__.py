from flask import Blueprint

from web.webhooks.asterisk import asterisk_bp
from web.webhooks.smsru import smsru_bp

webhooks_bp = Blueprint('webhook', __name__)

bluepints = [
    smsru_bp,
    asterisk_bp,
]

for bp in bluepints:
    webhooks_bp.register_blueprint(bp)
