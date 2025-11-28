from core.database.models import Model
from core.database.session import engine


def create_all():
    import core.database.models.employee
    import core.database.models.employee_phone
    import core.database.models.wifi_client
    import core.database.models.clients_number
    import core.database.models.blacklist

    Model.metadata.create_all(engine)
