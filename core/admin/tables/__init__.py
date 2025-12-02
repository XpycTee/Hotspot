from core.admin.tables.blacklist import delete_from_blacklist, get_blacklist
from core.admin.tables.employee import delete_from_employees, get_employees
from core.admin.tables.wifi_clients import get_wifi_clients


def get_table(table_name, page, rows_per_page, search_query):
    if table_name == 'wifi_clients':
        response = get_wifi_clients(page, rows_per_page, search_query)
        data = response.get('wifi_clients')
        total_rows = response.get('total_rows')

    elif table_name == 'employees':
        response = get_employees(page, rows_per_page, search_query)
        data = response.get('employees')
        total_rows = response.get('total_rows')

    elif table_name == 'blacklist':
        response = get_blacklist(page, rows_per_page, search_query)
        data = response.get('blacklist')
        total_rows = response.get('total_rows')

    else:
        return None
    
    return data, total_rows
