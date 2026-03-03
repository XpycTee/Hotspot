import os
from pathlib import Path


if "HOTSPOT_DB_URL" not in os.environ:
    test_db_path = Path(__file__).resolve().parents[1] / "hotspot_test.db"
    os.environ["HOTSPOT_DB_URL"] = f"sqlite:///{test_db_path.as_posix()}"

from core import database

database.create_all()
