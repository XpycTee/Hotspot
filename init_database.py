from sqlalchemy import update
from core.database.models import Model
from core.database.session import engine, get_session

import core.database.models.employee
import core.database.models.employee_phone
import core.database.models.wifi_client
import core.database.models.clients_number
import core.database.models.blacklist

Model.metadata.create_all(engine)


with get_session() as db_session:
    query = update(core.database.models.wifi_client.WifiClient).values(online=False)
    db_session.execute(query)
    db_session.commit()
