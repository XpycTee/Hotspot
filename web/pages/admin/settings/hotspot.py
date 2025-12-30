from dataclasses import replace
from datetime import timedelta
from flask import Blueprint, jsonify, render_template, request

from core.config.models import HotspotUserConfig
from core.config.store import ConfigLoader
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
    config = ConfigLoader().load()
    online_timeout = int(config.hotspot.online_timeout.total_seconds() / 60)

    staff_delay = timedelta_to_dhm(config.hotspot.staff.delay)
    guest_delay = timedelta_to_dhm(config.hotspot.guest.delay)

    template = render_template(
        'admin/settings/hotspot.html', 
        online_timeout=online_timeout,
        staff_delay=staff_delay,
        guest_delay=guest_delay
    )
    
    return template


def user_update(user: HotspotUserConfig, password: str = None, delay: timedelta = None) -> HotspotUserConfig:
    replaces = {}
    if delay:
        replaces['delay'] = delay
    if password:
        replaces['password'] = password
    
    return replace(user, **replaces)


@hotspot_bp.route('/update', methods=['POST'])
@login_required
def update():
    data: dict = request.json

    online_timeout = timedelta(minutes=data.get('online_timeout', 0))
    staff = data.get('staff', {})
    guest = data.get('guest', {})

    with ConfigLoader().update() as config:
        if online_timeout and online_timeout != config.hotspot.online_timeout:
            config.hotspot.online_timeout = online_timeout

        staff_delay = timedelta(seconds=staff.get('delay', 0))
        staff_pwd = staff.get('password', '')
        config.hotspot.staff = user_update(config.hotspot.staff, staff_pwd, staff_delay)

        guest_delay = timedelta(seconds=guest.get('delay', 0))
        guest_pwd = staff.get('password', '')
        config.hotspot.guest = user_update(config.hotspot.guest, guest_pwd, guest_delay)

    return jsonify({'success': True})
