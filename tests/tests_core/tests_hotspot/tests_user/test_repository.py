import datetime
import unittest
from unittest.mock import patch

from sqlalchemy import select

from core import database
from core.database.models import Model
from core.database.models.clients_number import ClientsNumber
from core.database.session import get_session
from core.hotspot.user.repository import get_or_create_clients_number, update_clients_numbers_last_seen


class TestCoreHotpsotUserRepository(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        database.create_all()

    def tearDown(self):
        self._clear_users()
    
    @staticmethod
    def _clear_users():
        with get_session() as db_session:
            for table in reversed(Model.metadata.sorted_tables):
                db_session.execute(table.delete())
            db_session.commit()

    @staticmethod
    def _db_add_clinet_number(phone_number='70000000001'):
        now_time = datetime.datetime.now()
        with get_session() as db_session:
            db_phone = ClientsNumber(phone_number=phone_number, last_seen=now_time)
            db_session.add(db_phone)
            db_session.commit()

    def test_get_or_create_clients_number(self):
        with get_session() as db_session:
            query = select(ClientsNumber).where(ClientsNumber.phone_number=='79999999901')
            client_number = db_session.scalars(query).first()
            self.assertIsNone(client_number)

        result = get_or_create_clients_number('79999999901')
        self.assertIsNotNone(result)

        with get_session() as db_session:
            query = select(ClientsNumber).where(ClientsNumber.phone_number=='79999999901')
            client_number = db_session.scalars(query).first()
            self.assertIsNotNone(client_number)

    @patch('core.hotspot.user.repository.datetime')
    def test_update_clients_numbers_last_seen(self, mock_datetime):
        self._db_add_clinet_number('70000000001')

        current_time = datetime.datetime.combine(
            datetime.date.today(), 
            datetime.time(10, 0)
        )
        mock_datetime.datetime.now.return_value = current_time
        update_clients_numbers_last_seen('70000000001')

        with get_session() as db_session:
            query = select(ClientsNumber).where(ClientsNumber.phone_number=='70000000001')
            client_number = db_session.scalars(query).first()
            self.assertEqual(client_number.last_seen, current_time)
