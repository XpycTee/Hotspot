from flask import Blueprint, render_template, session

from web.pages.admin.utils import login_required
from web.pages.admin.settings.radius import radius_bp
from web.pages.admin.settings.hotspot import hotspot_bp
from web.pages.admin.settings.users import users_bp
from web.pages.admin.settings.verificators import verificators_bp

settings_bp = Blueprint('settings', __name__, url_prefix='/settings')

bluepints = [
    radius_bp,
    hotspot_bp,
    users_bp,
    verificators_bp,
]

for bp in bluepints:
    settings_bp.register_blueprint(bp)


@settings_bp.route('', methods=['POST', 'GET'])
@login_required(group='full')
def index():
    error = session.pop('error', None)

    return render_template(
        'admin/settings.html', 
        error=error,
    )
