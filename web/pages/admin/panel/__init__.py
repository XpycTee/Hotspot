from flask import Blueprint, redirect, render_template, request, url_for

from core.hotspot.wifi.repository import get_locations
from web.pages.admin.utils import login_required


panel_bp = Blueprint('panel', __name__, url_prefix='/panel')


TOGGLE_STATE = {
    'all': 1,
    'yes': 2,
    'no': 3,
}


@panel_bp.route('', methods=['GET'])
@login_required
def index():
    return redirect(url_for('pages.admin.panel.wifi_clients'), 302)


@panel_bp.route('/wifi-clients', methods=['GET'])
@login_required
def wifi_clients():
    employee = request.args.get('employee', 'all')
    online = request.args.get('online', 'all')

    return render_template(
        'admin/panel/wifi_clients.html',
        locations=get_locations(),
        employee_state=TOGGLE_STATE.get(employee, 1),
        online_state=TOGGLE_STATE.get(online, 1),
    )


@panel_bp.route('/employees', methods=['GET'])
@login_required
def employees():
    return render_template('admin/panel/employees.html')


@panel_bp.route('/blacklist', methods=['GET'])
@login_required
def blacklist():
    return render_template('admin/panel/blacklist.html')
