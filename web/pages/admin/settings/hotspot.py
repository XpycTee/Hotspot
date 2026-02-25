from dataclasses import replace
from datetime import timedelta
from flask import Blueprint, render_template, request

from core.config.models.hotspot import HotspotUserConfig
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


def user_update(user: HotspotUserConfig, password: str = None, delay: timedelta = None) -> HotspotUserConfig:
    replaces = {}
    if delay:
        replaces['delay'] = delay
    if password:
        replaces['password'] = password
    
    return replace(user, **replaces)


@hotspot_bp.route('', methods=['POST', 'GET'])
@login_required(group='full')
def index():
    if request.method == 'POST':
        data: dict = request.form

        online_timeout = timedelta(minutes=data.get('online_timeout', 0, type=int))
        language = data.get('language', None, type=str)

        staff_pwd = data.get('staff_password', None, type=str)
        staff_delay = timedelta(
            days=data.get('staff_delay_days', 0, type=int),
            hours=data.get('staff_delay_hours', 0, type=int),
            minutes=data.get('staff_delay_minutes', 0, type=int)
        )

        guest_pwd = data.get('guest_password', None, type=str)
        guest_delay = timedelta(
            days=data.get('guest_delay_days', 0, type=int),
            hours=data.get('guest_delay_hours', 0, type=int),
            minutes=data.get('guest_delay_minutes', 0, type=int)
        )

        with ConfigLoader().update() as config:
            if online_timeout and online_timeout != config.hotspot.online_timeout:
                config.hotspot.online_timeout = online_timeout

            if language:
                config.language.name = language

            config.hotspot.staff = user_update(config.hotspot.staff, staff_pwd, staff_delay)
            config.hotspot.guest = user_update(config.hotspot.guest, guest_pwd, guest_delay)

    config = ConfigLoader().load()
    online_timeout = int(config.hotspot.online_timeout.total_seconds() / 60)

    staff_delay = timedelta_to_dhm(config.hotspot.staff.delay)
    guest_delay = timedelta_to_dhm(config.hotspot.guest.delay)

    template = render_template(
        'admin/settings/hotspot.html', 
        online_timeout=online_timeout,
        staff_delay=staff_delay,
        guest_delay=guest_delay,
        language=config.language.name
    )
    
    return template
