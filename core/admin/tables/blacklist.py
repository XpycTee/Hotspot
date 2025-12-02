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


def delete_from_blacklist(phone_number):
    with get_session() as db_session:
        query = select(Blacklist).where(Blacklist.phone_number==phone_number)
        blacklist_entry = db_session.scalars(query).first()
        if blacklist_entry:
            db_session.delete(blacklist_entry)
            db_session.commit()
    return {'status': 'OK'} # TODO

def update_blacklist():
    pass