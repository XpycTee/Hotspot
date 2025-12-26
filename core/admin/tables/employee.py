from sqlalchemy import or_, select
from core.database.models.employee import Employee
from core.database.models.employee_phone import EmployeePhone
from core.database.session import get_session
from core.logging import get_logger


logger = get_logger('core.admin.tbles.employee')

def get_employees(page: int, rows_per_page: int, search_query: str = None):
    with get_session() as db_session:
        query = select(Employee)

        if search_query:
            q = f'%{search_query}%'
            query = query.filter(or_(
                Employee.lastname.ilike(q),
                Employee.name.ilike(q),
                Employee.phones.any(
                    EmployeePhone.phone_number.ilike(q)
                )
            ))

        query = query.offset((page - 1) * rows_per_page).limit(rows_per_page)
        logger.debug(query)
        
        employees = db_session.scalars(query).all()
        
        total_rows = db_session.query(Employee).count()

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


def emoloyee_name(employee: Employee):
    if employee is not None:
        return  {
            'lastname': employee.lastname,
            'name': employee.name
        }
    return False
