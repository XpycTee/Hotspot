from sqlalchemy import select
from core.database.models.blacklist import Blacklist
from core.database.models.wifi_client import WifiClient
from core.database.session import get_session
from core.hotspot.user.expiration import reset_expiration
from core.utils.language import get_translate



def add_to_blacklist(phone_number):
    with get_session() as db_session:
        query = select(Blacklist).where(Blacklist.phone_number==phone_number)
        blocked_client = db_session.scalars(query).first()
        if blocked_client:
            return {'status': 'ALREDY_BLOCKED', 'error_message': get_translate('errors.admin.tables.phone_number_exists')}
        
        new_blacklist_entry = Blacklist(phone_number=phone_number)
        db_session.add(new_blacklist_entry)
        db_session.commit()

    return {'status': 'OK'}


def delete_from_blacklist(phone_number):
    with get_session() as db_session:
        query = select(Blacklist).where(Blacklist.phone_number==phone_number)
        blacklist_entry = db_session.scalars(query).first()
        if blacklist_entry:
            db_session.delete(blacklist_entry)
            db_session.commit()
    return {'status': 'OK'}


def add_to_blacklist_by_mac(mac):
    with get_session() as db_session:
        query = select(WifiClient).where(WifiClient.mac==mac)
        wifi_client = db_session.scalars(query).first()
        if not wifi_client:
            return {'status': 'NOT_FOUND', 'error_message': get_translate('errors.admin.tables.mac_not_found')}

        phone_number = wifi_client.phone.phone_number

    added = add_to_blacklist(phone_number)
    status = added.get('status')
    if status != 'OK':
        return added
    
    reset_expiration(mac)
    return {'status': 'OK'}


def check_blacklist(phone_number) -> bool:
    with get_session() as db_session:
        query = select(Blacklist).where(Blacklist.phone_number==phone_number)
        blocked_client = db_session.scalars(query).first()
        return blocked_client is not None
