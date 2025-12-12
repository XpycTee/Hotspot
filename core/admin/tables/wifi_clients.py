import datetime
from sqlalchemy import and_, select

from core.database.models.clients_number import ClientsNumber
from core.database.models.wifi_client import WifiClient
from core.database.session import get_session
from core.logging.logger import logger


def get_wifi_clients(page: int, rows_per_page: int, search_query: str = None,
                    online='all', employee='all', 
                    date_from=None, date_to=None, 
                    location=None):
    with get_session() as db_session:
        query = select(WifiClient)

        filters = []

        if search_query:
            search_filters = (
                WifiClient.mac.ilike(f'%{search_query}%') |
                WifiClient.last_location.ilike(f'%{search_query}%') |
                WifiClient.phone.has(ClientsNumber.phone_number.ilike(f'%{search_query}%'))
            )
            filters.append(search_filters)

        if online == 'yes':
            filters.append(WifiClient.online==True)
        elif online == 'no':
            filters.append(WifiClient.online==False)
        if employee == 'yes':
            filters.append(WifiClient.employee==True)
        elif employee == 'no':
            filters.append(WifiClient.employee==False)
        if date_from:
            date_from = datetime.datetime.fromisoformat(date_from)
            filters.append(WifiClient.expiration>=date_from)
        if date_to:
            date_to = datetime.datetime.fromisoformat(date_to)
            date_to += datetime.timedelta(hours=12)
            filters.append(WifiClient.expiration<=date_to)
        if location:
            filters.append(WifiClient.last_location==location)

        if filters:
            query = query.filter(and_(*filters))


        query = query.offset((page - 1) * rows_per_page).limit(rows_per_page)
        logger.debug(query)

        clients = db_session.scalars(query).all()

        total_rows = db_session.query(WifiClient).count()

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
