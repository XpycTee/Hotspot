from flask import Blueprint, redirect, url_for

from web.pages.admin.auth import auth_bp
from web.pages.admin.tables import tables_bp
from web.pages.admin.hotspot import hotspot_bp
from web.pages.admin.panel import panel_bp
from web.pages.admin.settings import settings_bp

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

bluepints = [
    auth_bp,
    panel_bp,
    tables_bp,
    hotspot_bp,
    settings_bp
]

for bp in bluepints:
    admin_bp.register_blueprint(bp)


@admin_bp.route('', methods=['POST', 'GET'])
def index():
    return redirect(url_for('pages.admin.panel.index'), 302)
