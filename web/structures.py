from dataclasses import dataclass
from enum import Enum
from typing import List, Mapping

class ViewFieldType(str, Enum):
    CHECKBOX = 'checkbox'
    RADIO = 'radio'
    TEXT = 'text'
    SELECT = 'select'
    PASSWORD = 'password'
    PASSWORD_CONFIRM = 'passowrd'
    USERNAME = 'text'

@dataclass
class ViewItemField:
    name: str
    label: str
    type: ViewFieldType
    required: bool = True
    value: str | Mapping[str, bool] | None = None

@dataclass
class ViewItem:
    name: str
    enabled: bool
    fields: List[ViewItemField]
    actions: List[str]
