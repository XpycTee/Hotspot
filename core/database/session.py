from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from core.bootstrap.env import DB_URL
from core.utils import json


engine = create_engine(
    DB_URL,
    json_serializer=lambda obj: json.dumps(obj).decode("utf-8"),
    json_deserializer=lambda s: json.loads(s.encode("utf-8")),
)
SessionLocal = sessionmaker(bind=engine)

@contextmanager
def get_session():
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except:
        session.rollback()
        raise
    finally:
        session.close()
