from core.admin.repository import create_user
from core.bootstrap.env import ADMIN_PASSWORD, ADMIN_USERNAME
from core.database import create_all

create_all()
create_user(ADMIN_USERNAME, ADMIN_PASSWORD, 'full')