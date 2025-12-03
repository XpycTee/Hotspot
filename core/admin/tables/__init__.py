from core.admin.tables.blacklist import get_blacklist
from core.admin.tables.employee import get_employees
from core.admin.tables.wifi_clients import get_wifi_clients


def get_table(table_name: str, page: int, rows_per_page: int, search_query: str = None):
    if table_name == 'wifi_clients':
        response = get_wifi_clients(page, rows_per_page, search_query)
    elif table_name == 'employees':
        response = get_employees(page, rows_per_page, search_query)
    elif table_name == 'blacklist':
        response = get_blacklist(page, rows_per_page, search_query)
    else:
        return None
    
    data = response.get(table_name)
    total_rows = response.get('total_rows')

    return data, total_rows
