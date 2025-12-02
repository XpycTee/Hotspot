from flask import Blueprint, redirect, render_template, session, url_for

from web.pages.admin.auth import auth_bp
from web.pages.admin.tables import tables_bp
from web.pages.admin.hotspot import hotspot_bp
from web.pages.admin.utils import login_required

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

bluepints = [
    auth_bp,
    tables_bp,
    hotspot_bp
]

for bp in bluepints:
    admin_bp.register_blueprint(bp)


@admin_bp.route('/', methods=['POST', 'GET'])
@login_required
def admin():
    return redirect(url_for('pages.admin.panel'), 302)


@admin_bp.route('/panel', methods=['POST', 'GET'])
@login_required
def panel():
    error = session.pop('error', None)
    return render_template('admin/panel.html', error=error)
