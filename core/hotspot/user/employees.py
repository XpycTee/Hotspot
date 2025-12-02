from core.database.models.employee import Employee
from core.database.models.employee_phone import EmployeePhone
from core.database.session import get_session


from sqlalchemy import select

from core.utils.language import get_translate
from core.utils.phone import normalize_phone


def delete_from_employees(employee_id):
    with get_session() as db_session:
        query = select(Employee).where(Employee.id==employee_id)
        employee = db_session.scalars(query).first()

        if not employee:
            return {'status': 'NOT_FOUND'}

        # Удаление всех связанных телефонов
        for phone in employee.phones:
            db_session.delete(phone)
        db_session.delete(employee)
        db_session.commit()
    return {'status': 'OK'}


def add_employee(lastname: str, name: str, phone_numbers: list):
    # Создание нового сотрудника
    with get_session() as db_session:
        new_employee = Employee(lastname=lastname, name=name)
        db_session.add(new_employee)
        db_session.flush()  # Чтобы получить ID нового сотрудника

        # Добавление телефонов
        for phone_number in phone_numbers:
            phone_number = normalize_phone(phone_number)
            query = select(EmployeePhone).where(EmployeePhone.phone_number==phone_number)
            employee_phone = db_session.scalars(query).first()
            if employee_phone:
                return {'status': 'ALREDY_EXISTS', 'error_message': get_translate('errors.admin.tables.phone_number_exists')}
            new_phone = EmployeePhone(phone_number=phone_number, employee=new_employee)
            db_session.add(new_phone)
        new_id = new_employee.id
    return {'status': 'OK', 'employee_id': new_id}


def update_employee(employee_id, lastname: str=None, name: str=None, phone_numbers=[]):
    if lastname is None and name is None and phone_number == []:
        return {'status': 'BAD_REUQEST'}

    with get_session() as db_session:
        query = select(Employee).where(Employee.id==employee_id)
        employee = db_session.scalars(query).first()

        if not employee:
            return {'status': 'NOT_FOUND', 'error_message': get_translate('errors.admin.tables.employee_not_found')}

        # Обновление существующего сотрудника
        if lastname:
            employee.lastname = lastname
        if name:
            employee.name = name

        # Обновление телефонов сотрудника
        existing_phones = {phone.phone_number for phone in employee.phones}
        new_phones = set()

        for phone_number in phone_numbers:
            phone_number = normalize_phone(phone_number)
            new_phones.add(phone_number)

        # Удаление старых телефонов
        for phone in employee.phones:
            if phone.phone_number not in new_phones:
                db_session.delete(phone)

        # Добавление новых телефонов
        for phone_number in new_phones - existing_phones:
            new_phone = EmployeePhone(phone_number=phone_number, employee=employee)
            db_session.add(new_phone)

    return {'status': 'OK'}