from datetime import datetime, timedelta
from functools import wraps

from flask import (
    Blueprint, abort, render_template, redirect, url_for,
    session, request, current_app, jsonify
)

from core.admin.auth.login import login_by_password
from core.config.language import LANGUAGE_DEFAULT
from core.utils.language import get_translate
from core.utils.phone import normalize_phone
import web.logger as logger

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


def login_required(f):
    """Декоратор для проверки авторизации."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        logger.debug(f'session data {[item for item in session.items()]}')
        if not session.get('is_authenticated'):
            logger.debug('User is not authenticated')
            return redirect(url_for('admin.login'), 302)
        return f(*args, **kwargs)
    return decorated_function


def _log_masked_session():
    sensetive = []
    result = {}
    items = session.items()
    for k, v in items:
        if k.startswith("_"):
            continue
        elif k in sensetive:
            result[k] = '******'
        else:
            result[k] = v
    return result


@admin_bp.route('/', methods=['POST', 'GET'])
@login_required
def admin():
    return redirect(url_for('admin.panel'), 302)


@admin_bp.route('/login', methods=['POST', 'GET'])
def login():
    error = session.pop('error', None)
    return render_template('admin/login.html', error=error)


@admin_bp.route('/auth', methods=['POST'])
def auth():
    username = request.form.get('username')
    password = request.form.get('password')
    client_ip = request.remote_addr
    user_lang = request.form.get('language', LANGUAGE_DEFAULT)

    session_id = session.get('_id')

    response = login_by_password(session_id, username, password)
    status = response.get('status')

    if status == 'OK':
        session['is_authenticated'] = True
        session['user_lang'] = user_lang if user_lang != 'auto' else None
        session.permanent = True 
        current_app.permanent_session_lifetime = timedelta(minutes=30)

        logger.info(f'User {username} logged in from {client_ip}')
        logger.debug(f'session data {_log_masked_session()}')
        return redirect(url_for('pages.admin.panel'), 302)

    if status == 'LOCKOUT':
        error_message = response.get('error_message')
        _set_error_and_log(error_message, username, client_ip)
        return redirect(url_for('pages.admin.login'), 302)
    
    if status == 'BAD_LOGIN':
        error_message = response.get('error_message')
        _set_error_and_log(error_message, username, client_ip)
        return redirect(url_for('pages.admin.login'), 302)

    abort(500)

@admin_bp.route('/panel', methods=['POST', 'GET'])
@login_required
def panel():
    error = session.pop('error', None)
    return render_template('admin/panel.html',error=error)


@admin_bp.route('/logout', methods=['POST', 'GET'])
def logout():
    session.clear()  # Очищаем сессию
    return redirect(url_for('admin.login'), 302)


@admin_bp.route('/save/<tabel_name>', methods=['POST'])
@login_required
def save_data(tabel_name):
    data = request.json
    new_id = None

    if not data:
        abort(400, description=get_translate('errors.admin.tables.missing_request_data'))

    if tabel_name == 'employee':
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
    elif tabel_name == 'blacklist':
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


@admin_bp.route('/delete/<tabel_name>', methods=['POST'])
@login_required
def delete_data(tabel_name):
    data = request.json

    if not data:
        abort(400, description=get_translate('errors.admin.tables.missing_request_data'))

    if tabel_name == 'employee':
        emp_id = data.get('id')
        if emp_id is None:
            abort(400, description=get_translate('errors.admin.tables.employee_not_found'))
        
        employee = Employee.query.filter_by(id=emp_id).first()

        if not employee:
            abort(404, description=get_translate('errors.admin.tables.employee_not_found'))

        # Удаление всех связанных телефонов
        for phone in employee.phones:
            db.session.delete(phone)
        db.session.delete(employee)
        db.session.commit()
    elif tabel_name == 'blacklist':
        blacklist_entry = Blacklist.query.filter_by(phone_number=data['phone']).first()
        if blacklist_entry:
            db.session.delete(blacklist_entry)
            db.session.commit()
    else:
        abort(404)

    return jsonify({'success': True})


@admin_bp.route('/deauth', methods=['POST'])
@login_required
def deauth():
    data = request.json
    if not data or 'mac' not in data:
        abort(400, description=get_translate('errors.admin.tables.mac_is_missing'))

    mac_address = data['mac']

    # Проверяем наличие клиента с указанным MAC-адресом
    wifi_client = WifiClient.query.filter_by(mac=mac_address).first()
    if not wifi_client:
        abort(404, description=get_translate('errors.admin.tables.mac_no_found'))

    # Устанавливаем срок истечения равным началу отсчета времени
    wifi_client.expiration = datetime(1970, 1, 1)  # Unix epoch start
    db.session.commit()

    return jsonify({'success': True})


@admin_bp.route('/block', methods=['POST'])
@login_required
def block():
    data = request.json
    if not data or 'mac' not in data:
        abort(400, description=get_translate('errors.admin.tables.mac_is_missing'))

    mac_address = data['mac']

    # Проверяем наличие клиента с указанным MAC-адресом
    wifi_client = WifiClient.query.filter_by(mac=mac_address).first()
    if not wifi_client:
        abort(404, description=get_translate('errors.admin.tables.mac_no_found'))

    phone_number = wifi_client.phone.phone_number
    
    if Blacklist.query.filter_by(phone_number=phone_number).first():
        abort(400, description=get_translate('errors.admin.tables.phone_number_exists'))
        
    new_blacklist_entry = Blacklist(phone_number=phone_number)
    db.session.add(new_blacklist_entry)
    db.session.commit()

    # Устанавливаем срок истечения равным началу отсчета времени
    wifi_client.expiration = datetime(1970, 1, 1)  # Unix epoch start
    db.session.commit()

    return jsonify({'success': True})


@admin_bp.route('/table/<tabel_name>', methods=['GET'])
@login_required
def get_tabel(tabel_name):
    search_query = request.args.get('search', '').lower()
    page = int(request.args.get('page', 1))
    rows_per_page = int(request.args.get('rows_per_page', 10))

    if tabel_name == 'wifi_clients':
        query = WifiClient.query.join(ClientsNumber, WifiClient.phone_id == ClientsNumber.id)
        if search_query:
            query = query.filter(
                WifiClient.mac.ilike(f'%{search_query}%') |
                WifiClient.phone.has(ClientsNumber.phone_number.ilike(f'%{search_query}%'))
            )

        employee_delay = current_app.config['HOTSPOT_USERS']['employee']['delay']
        guest_delay = current_app.config['HOTSPOT_USERS']['guest']['delay']

        # Сортируем по вычисляемому выражению
        query = query.order_by(
            db.desc(
                WifiClient.expiration - db.case(
                    (WifiClient.employee == True, employee_delay),
                    else_=guest_delay
                )
            )
        )   

        total_rows = query.count()
        logger.debug(query.statement.compile())
        clients = query.offset((page - 1) * rows_per_page).limit(rows_per_page).all()

        data = [
            {
                'mac': client.mac,
                'expiration': client.expiration,
                'employee': client.employee,
                'phone': client.phone.phone_number if client.phone else None
            }
            for client in clients
        ]
    elif tabel_name == 'employee':
        query = Employee.query

        if search_query:
            query = query.filter(
                Employee.lastname.ilike(f'%{search_query}%') |
                Employee.name.ilike(f'%{search_query}%') |
                Employee.phones.any(EmployeePhone.phone_number.ilike(f'%{search_query}%'))
            )

        total_rows = query.count()
        employees = query.offset((page - 1) * rows_per_page).limit(rows_per_page).all()

        data = [
        {
            'id': emp.id,
            'lastname': emp.lastname,
            'name': emp.name,
            'phones': [phone.phone_number for phone in emp.phones]
        }
        for emp in employees
    ]
    elif tabel_name == 'blacklist':
        query = Blacklist.query

        if search_query:
            query = query.filter(Blacklist.phone_number.ilike(f'%{search_query}%'))

        total_rows = query.count()
        blacklist = query.offset((page - 1) * rows_per_page).limit(rows_per_page).all()

        data = [entry.phone_number for entry in blacklist]
    else:
        abort(404)

    return jsonify({
        'data': data,
        'total_rows': total_rows,
        'current_page': page,
        'rows_per_page': rows_per_page
    })


def _set_error_and_log(message, username, client_ip):
    """Устанавливает сообщение об ошибке и записывает лог."""
    session['error'] = message
    logger.error(f"{message} for user {username} from {client_ip}")