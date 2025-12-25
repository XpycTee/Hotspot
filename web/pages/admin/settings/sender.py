from flask import Blueprint, render_template

from core.config import CONFIG
from web.pages.admin.utils import login_required


sender_bp = Blueprint('sender', __name__, url_prefix='/sender')


@sender_bp.route('', methods=['GET'])
@login_required
def index():

    template = render_template(
        'admin/settings/sender.html',
        sender=CONFIG.sender
    )
    
    return template
