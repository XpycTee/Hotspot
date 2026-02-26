from flask import Blueprint, redirect, render_template, request, url_for

from core.admin.tables.blacklist import get_blacklist
from core.admin.tables.employee import get_employees
from core.hotspot.wifi.repository import get_locations
from web.pages.admin.utils import login_required
from web.structures import ViewFieldType, ViewItem, ViewItemField


panel_bp = Blueprint('panel', __name__, url_prefix='/panel')


TOGGLE_STATE = {
    'all': 1,
    'yes': 2,
    'no': 3,
}


EMPLOYEE_ITEM_ACTIONS = ['save', 'delete']
BLACKLIST_ITEM_ACTIONS = ['delete']
DEFAULT_ENABLED = True


def _build_employee_item(data: dict) -> ViewItem:
    full_name = f"{data.get('lastname', '').strip()} {data.get('name', '').strip()}".strip()
    phones = data.get('phones', [])

    return ViewItem(
        name=full_name or f"Employee #{data.get('id')}",
        enabled=DEFAULT_ENABLED,
        fields=[
            ViewItemField(
                name='lastname',
                label='Lastname',
                type=ViewFieldType.TEXT,
                value=data.get('lastname', ''),
            ),
            ViewItemField(
                name='name',
                label='Name',
                type=ViewFieldType.TEXT,
                value=data.get('name', ''),
            ),
            ViewItemField(
                name='phone',
                label='Phones',
                type=ViewFieldType.LIST,
                value=phones,
                required=True,
            ),
        ],
        actions=EMPLOYEE_ITEM_ACTIONS,
    )


def _build_empty_employee_item() -> ViewItem:
    return ViewItem(
        name='New Employee',
        enabled=DEFAULT_ENABLED,
        fields=[
            ViewItemField(
                name='lastname',
                label='Lastname',
                type=ViewFieldType.TEXT,
            ),
            ViewItemField(
                name='name',
                label='Name',
                type=ViewFieldType.TEXT,
            ),
            ViewItemField(
                name='phone',
                label='Phones',
                type=ViewFieldType.LIST,
                value=[''],
                required=True,
            ),
        ],
        actions=EMPLOYEE_ITEM_ACTIONS,
    )


def _build_blacklist_item(phone_number: str) -> ViewItem:
    return ViewItem(
        name=f'+{phone_number}',
        enabled=DEFAULT_ENABLED,
        fields=[
            ViewItemField(
                name='phone',
                label='Phone',
                type=ViewFieldType.TEXT,
                value=phone_number,
            ),
        ],
        actions=BLACKLIST_ITEM_ACTIONS,
    )


def _build_empty_blacklist_item() -> ViewItem:
    return ViewItem(
        name='New Blocked Number',
        enabled=DEFAULT_ENABLED,
        fields=[
            ViewItemField(
                name='phone',
                label='Phone',
                type=ViewFieldType.TEXT,
            ),
        ],
        actions=['save', 'delete'],
    )


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
    employees_data = get_employees(1, 1000000).get('employees', [])
    data = {
        str(employee.get('id')): _build_employee_item(employee)
        for employee in employees_data
    }

    return render_template(
        'admin/panel/employees.html',
        data=data,
        actions=['add'],
        empty_item=_build_empty_employee_item(),
    )


@panel_bp.route('/blacklist', methods=['GET'])
@login_required
def blacklist():
    blacklist_data = get_blacklist(1, 1000000).get('blacklist', [])
    data = {phone_number: _build_blacklist_item(phone_number) for phone_number in blacklist_data}

    return render_template(
        'admin/panel/blacklist.html',
        data=data,
        actions=['add'],
        empty_item=_build_empty_blacklist_item(),
    )
