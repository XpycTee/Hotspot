from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from core.db.models import Model

DB_URL = 'sqlite:///config/hotspot.db'

engine = create_engine(DB_URL)
SessionLocal = sessionmaker(bind=engine)

def create_all():
    import core.db.models.employee
    import core.db.models.employee_phone
    import core.db.models.wifi_client
    import core.db.models.clients_number
    import core.db.models.blacklist

    Model.metadata.create_all(engine)

    