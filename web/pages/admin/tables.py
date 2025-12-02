from flask import Blueprint, abort, jsonify, request

from core.admin.tables import get_table
from core.admin.tables.blacklist import delete_from_blacklist
from core.admin.tables.employee import delete_from_employees
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

    if table_name == 'employee':
        emp_id = data.get('id')
        if emp_id is not None:
            employee = Employee.query.filter_by(id=emp_id).first()
            if not employee:
                abort(404, description=get_translate('errors.admin.tables.employee_not_found'))

            # Обновление существующего сотрудника
            employee.lastname = data['lastname']
            employee.name = data['name']

            # Обновление телефонов сотрудника
            existing_phones = {phone.phone_number for phone in employee.phones}
            new_phones = set()

            for phone_number in data['phone']:
                phone_number = normalize_phone(phone_number)
                new_phones.add(phone_number)

            # Удаление старых телефонов
            for phone in employee.phones:
                if phone.phone_number not in new_phones:
                    db.session.delete(phone)

            # Добавление новых телефонов
            for phone_number in new_phones - existing_phones:
                new_phone = EmployeePhone(phone_number=phone_number, employee=employee)
                db.session.add(new_phone)
        else:
            # Создание нового сотрудника
            new_employee = Employee(lastname=data['lastname'], name=data['name'])
            db.session.add(new_employee)
            db.session.flush()  # Чтобы получить ID нового сотрудника

            # Добавление телефонов
            for phone_number in data['phone']:
                phone_number = normalize_phone(phone_number)
                if EmployeePhone.query.filter_by(phone_number=phone_number).first():
                    abort(400, description=get_translate('errors.admin.tables.phone_number_exists'))
                new_phone = EmployeePhone(phone_number=phone_number, employee=new_employee)
                db.session.add(new_phone)
            new_id = new_employee.id
        db.session.commit()
    elif table_name == 'blacklist':
        if Blacklist.query.filter_by(phone_number=data['phone']).first():
            abort(400, description=get_translate('errors.admin.tables.phone_number_exists'))
        
        phone_number = normalize_phone(data['phone'])

        new_blacklist_entry = Blacklist(phone_number=phone_number)
        db.session.add(new_blacklist_entry)
        db.session.commit()
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
            abort(500, description='Unknown status')
    elif table_name == 'blacklist':
        phone_number = data.get('phone')
        if not phone_number:
            abort(400, description=get_translate('errors.admin.tables.phone_not_found'))
        response = delete_from_blacklist(phone_number)
        status = response.get('status')
        if status != 'OK':
            abort(500, description='Unknown status')
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
