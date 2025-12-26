from datetime import timedelta
from flask import Blueprint, jsonify, render_template, request

from core.config import CONFIG
from core.config.store import ConfigStore
from web.pages.admin.utils import login_required

hotspot_bp = Blueprint('hotspot', __name__, url_prefix='/hotspot')


def timedelta_to_dhm(td: timedelta) -> dict[str, int]:
    total_minutes = int(td.total_seconds() // 60)

    days, rem_minutes = divmod(total_minutes, 24 * 60)
    hours, minutes = divmod(rem_minutes, 60)

    return {
        "days": days,
        "hours": hours,
        "minutes": minutes,
    }


@hotspot_bp.route('', methods=['POST', 'GET'])
@login_required
def index():
    online_timeout = int(CONFIG.hotspot.online_timeout.total_seconds() / 60)

    staff_delay = timedelta_to_dhm(CONFIG.hotspot.staff.delay)
    guest_delay = timedelta_to_dhm(CONFIG.hotspot.guest.delay)

    template = render_template(
        'admin/settings/hotspot.html', 
        online_timeout=online_timeout,
        staff_delay=staff_delay,
        guest_delay=guest_delay
    )
    
    return template


@hotspot_bp.route('/update', methods=['POST'])
@login_required
def update():
    data: dict = request.json

    online_timeout = timedelta(minutes=data.get('online_timeout', 0))
    if online_timeout and online_timeout != CONFIG.hotspot.online_timeout:
        CONFIG.hotspot.online_timeout = online_timeout

    staff = data.get('staff', {})

    staff_delay = timedelta(seconds=staff.get('delay', 0))
    if staff_delay:
        CONFIG.hotspot.staff.delay = staff_delay

    staff_pwd = staff.get('password', '')
    if staff_pwd:
        CONFIG.hotspot.staff.password = staff_pwd

    guest = data.get('guest', {})

    guest_delay = timedelta(seconds=guest.get('delay', 0))
    if guest_delay:
        CONFIG.hotspot.guest.delay = guest_delay

    guest_pwd = staff.get('password', '')
    if guest_pwd:
        CONFIG.hotspot.guest.password = guest_pwd


    store = ConfigStore()
    store.save()

    return jsonify({'success': True})
