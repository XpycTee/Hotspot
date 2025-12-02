from sqlalchemy import select
from core.database.models.blacklist import Blacklist
from core.database.session import get_session
from core.logging.logger import logger


def get_blacklist(page: int, rows_per_page: int, search_query):
    with get_session() as db_session:
        query = select(Blacklist)

        if search_query:
            query = query.filter(Blacklist.phone_number.ilike(f'%{search_query}%'))

        query = query.offset((page - 1) * rows_per_page).limit(rows_per_page)
        logger.debug(query)
        
        blacklist = db_session.scalars(query).all()
        total_rows = len(blacklist)

        data = [entry.phone_number for entry in blacklist]
    return {'blacklist': data, 'total_rows': total_rows}
