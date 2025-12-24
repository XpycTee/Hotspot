from sqlalchemy import (
    Column,
    Integer,
    DateTime,
    CheckConstraint,
    func,
)
from sqlalchemy.dialects.sqlite import JSON as SQLiteJSON
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.types import JSON
from sqlalchemy.orm import mapped_column
from core.database.models import Model


def JSONType(): 
    """ Унифицированный 
    JSON: 
    - SQLite -> JSON (text) 
    - Postgres -> JSONB 
    - MySQL -> JSON 
    """ 
    return JSON().with_variant(SQLiteJSON, "sqlite").with_variant(JSONB, "postgresql")


class MutableDataclassDict(MutableDict):
    @classmethod
    def coerce(cls, key, value):
        if isinstance(value, dict):
            return super().coerce(key, value)
        from core.utils.json import dataclass_to_dict
        from dataclasses import is_dataclass
        if is_dataclass(value):
            return super().coerce(key, dataclass_to_dict(value))
        return super().coerce(key, value)


class SystemConfig(Model):
    __tablename__ = "system_config"

    id = Column(Integer, primary_key=True, default=1)
    version = Column(Integer, nullable=False, default=1)
    data = Column(MutableDataclassDict.as_mutable(JSONType()), nullable=False, default=dict)
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        CheckConstraint("id = 1", name="only_one_row"),
    )

    def to_dict(self) -> dict:
        return {
            "version": self.version,
            "data": self.data,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
