from sqlalchemy import select
from core.database.models.employee import Employee
from core.database.models.employee_phone import EmployeePhone
from core.database.session import get_session
from core.logging.logger import logger


def get_employees(page: int, rows_per_page: int, search_query):
    with get_session() as db_session:
        query = select(Employee)

        if search_query:
            query = query.filter(
                Employee.lastname.ilike(f'%{search_query}%') |
                Employee.name.ilike(f'%{search_query}%') |
                Employee.phones.any(EmployeePhone.phone_number.ilike(f'%{search_query}%'))
            )

        query = query.offset((page - 1) * rows_per_page).limit(rows_per_page)
        logger.debug(query)
        
        employees = db_session.scalars(query).all()
        total_rows = len(employees)

        data = [
            {
                'id': emp.id,
                'lastname': emp.lastname,
                'name': emp.name,
                'phones': [phone.phone_number for phone in emp.phones]
            }
            for emp in employees
        ]
    return {'employees': data, 'total_rows': total_rows}


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


def update_employees():
    pass
