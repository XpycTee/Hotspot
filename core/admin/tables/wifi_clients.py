from sqlalchemy import case, desc, select
from core.config.users import GUEST_USER, STAFF_USER
from core.database.models.clients_number import ClientsNumber
from core.database.models.wifi_client import WifiClient
from core.database.session import get_session
from core.logging.logger import logger


def get_wifi_clients(page: int, rows_per_page: int, search_query: str = None):
    with get_session() as db_session:
        query = select(WifiClient)

        if search_query:
            query = query.filter(
                WifiClient.mac.ilike(f'%{search_query}%') |
                WifiClient.phone.has(ClientsNumber.phone_number.ilike(f'%{search_query}%'))
            )

        staff_delay = STAFF_USER.get('delay')
        guest_delay = GUEST_USER.get('delay')

        query = query.order_by(
            desc(
                WifiClient.expiration - case(
                    (WifiClient.employee == True, staff_delay),
                    else_=guest_delay
                )
            )
        )
        query = query.offset((page - 1) * rows_per_page).limit(rows_per_page)
        logger.debug(query)

        clients = db_session.scalars(query).all()
        total_rows = len(clients)

        data = [
            {
                'mac': client.mac,
                'expiration': client.expiration,
                'employee': client.employee,
                'phone': client.phone.phone_number if client.phone else None,
                'online': client.online,
                'last_location': client.last_location,
                'last_ipv4_address': client.last_ipv4_address
            }
            for client in clients
        ]
    return {'wifi_clients': data, 'total_rows': total_rows}
