from flask import Blueprint, abort, jsonify, request

from core.admin.tables import get_table
from core.hotspot.user.blacklist import add_to_blacklist, delete_from_blacklist
from core.hotspot.user.employees import add_employee, delete_from_employees, update_employee
from core.utils.language import get_translate
from core.utils.phone import normalize_phone
from web.pages.admin.utils import login_required


tables_bp = Blueprint('tables', __name__, url_prefix='/tables')


@tables_bp.route('/<table_name>/save', methods=['POST'])
@login_required
def save_data(table_name):
    data = request.json
    new_id = None

    if not data:
        abort(400, description=get_translate('errors.admin.tables.missing_request_data'))

    if table_name == 'employees':
        employee_id = data.get('id')
        lastname = data.get('lastname')
        name = data.get('name')
        phone_numbers = data.get('phone')

        if employee_id is not None:
            response = update_employee(employee_id, lastname, name, phone_numbers)
            status = response.get('status')
            if status == 'NOT_FOUND':
                error_message = response.get('error_message')
                abort(404, description=error_message)
            elif status == 'BAD_REUQEST':
                abort(400)
            elif status != 'OK':
                abort(500, description=get_translate('errors.admin.tables.unknown_status'))
        else:
            response = add_employee(lastname, name, phone_numbers)
            status = response.get('status')
            if status == 'ALREDY_EXISTS':
                error_message = response.get('error_message')
                abort(400, description=error_message)
            elif status == 'OK':            
                new_id = response.get('employee_id')
            else:
                abort(500, description=get_translate('errors.admin.tables.unknown_status'))

    elif table_name == 'blacklist':
        phone_number = normalize_phone(data.get('phone'))
        response = add_to_blacklist(phone_number)
        status = response.get('status')
        if status == 'ALREDY_BLOCKED':
            error_message = response.get('error_message')
            abort(400, description=error_message)
        elif status != 'OK':
            abort(500, description=get_translate('errors.admin.tables.unknown_status'))
    
    else:
        abort(404)

    response = {'success': True}
    if new_id:
        response.update({'new_id': new_id})
    return jsonify(response)


@tables_bp.route('/<table_name>/delete', methods=['POST'])
@login_required
def delete_data(table_name):
    data = request.json

    if not data:
        abort(400, description=get_translate('errors.admin.tables.missing_request_data'))

    if table_name == 'employees':
        employee_id = data.get('id')
        if employee_id is None:
            abort(400, description=get_translate('errors.admin.tables.bad_employee_id'))
        response = delete_from_employees(employee_id)
        status = response.get('status')
        if status == 'NOT_FOUND':
            abort(404, description=get_translate('errors.admin.tables.employee_not_found'))
        elif status != 'OK':
            abort(500, description=get_translate('errors.admin.tables.unknown_status'))
    elif table_name == 'blacklist':
        phone_number = data.get('phone')
        if not phone_number:
            abort(400, description=get_translate('errors.admin.tables.phone_not_found'))
        response = delete_from_blacklist(phone_number)
        status = response.get('status')
        if status != 'OK':
            abort(500, description=get_translate('errors.admin.tables.unknown_status'))
    else:
        abort(404)

    return jsonify({'success': True})


@tables_bp.route('/<table_name>', methods=['GET'])
@login_required
def table(table_name):
    search_query = request.args.get('search', '').lower()
    page = int(request.args.get('page', 1))
    rows_per_page = int(request.args.get('rows_per_page', 10))

    response = get_table(table_name, page, rows_per_page, search_query)
    if not response:
        abort(404)
        
    data, total_rows = response
    return jsonify({
        'data': data,
        'total_rows': total_rows,
        'current_page': page,
        'rows_per_page': rows_per_page
    })
