from __future__ import annotations

import base64
from dataclasses import fields, is_dataclass
from datetime import datetime, date, timedelta
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from _typeshed import SupportsRead

import orjson


# ---------- SERIALIZATION ----------

def _default(obj: Any): 
    if is_dataclass(obj):
        return dataclass_to_dict(obj)  # рекурсивно, но безопасно
    
    # bytes / bytearray -> base64 with marker
    if isinstance(obj, (bytes, bytearray)):
        return {
            '__type__': 'bytes',
            'encoding': 'base64',
            'value': base64.b64encode(obj).decode('ascii'),
        }

    # datetime / date -> ISO (orjson умеет, но фиксируем явно)
    if isinstance(obj, (datetime, date)):
        return {
            '__type__': 'datetime',
            'format': 'iso',
            'value': obj.isoformat(),
        }

    if isinstance(obj, timedelta):
        return {
            '__type__': 'timedelta',
            'format': 'seconds',
            'value': obj.total_seconds(),
        }

    raise TypeError(f'Type is not JSON serializable: {type(obj)!r}')


def dumps(obj: Any, *, indent: bool = False) -> bytes:
    option = orjson.OPT_INDENT_2 if indent else 0
    return orjson.dumps(obj, default=_default, option=option)


# ---------- DESERIALIZATION ----------

def _restore(obj: Any):
    if isinstance(obj, dict):
        obj_type = obj.get('__type__')
        if obj_type == 'bytes':
            if obj.get('encoding') != 'base64':
                raise ValueError('Unsupported bytes encoding')
            return base64.b64decode(obj['value'])
        elif obj_type == 'datetime':
            if obj.get('format') != 'iso':
                raise ValueError('Unsupported datetime format')
            return datetime.fromisoformat(obj['value'])
        elif obj_type == 'timedelta':
            if (fmt:=obj.get('format')) not in ('seconds', 'minutes', 'hours', 'days'):
                raise ValueError('Unsupported timedelta format')
            return timedelta(**{fmt: obj['value']})
    return obj


def _walk(obj: Any):
    if isinstance(obj, dict):
        return {k: _walk(_restore(v)) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_walk(_restore(i)) for i in obj]
    return _restore(obj)


def loads(data: bytes) -> Any:
    raw = orjson.loads(data)
    return _walk(raw)


def load(fp: SupportsRead[bytes]) -> Any:
    raw = orjson.loads(fp.read())
    return _walk(raw)


def dataclass_to_dict(obj):
    if is_dataclass(obj):
        result = {}
        for f in fields(obj):
            if f.metadata.get('json') is False or f.name.startswith('_'):
                continue
            value = getattr(obj, f.name)
            result[f.name] = dataclass_to_dict(value)
        return result
    return obj
