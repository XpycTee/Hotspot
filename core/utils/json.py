from __future__ import annotations

import base64
from datetime import datetime, date
from typing import Any

import orjson


# ---------- SERIALIZATION ----------

def _default(obj: Any):
    # bytes / bytearray -> base64 with marker
    if isinstance(obj, (bytes, bytearray)):
        return {
            "__type__": "bytes",
            "encoding": "base64",
            "value": base64.b64encode(obj).decode("ascii"),
        }

    # datetime / date -> ISO (orjson умеет, но фиксируем явно)
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()

    raise TypeError(f"Type is not JSON serializable: {type(obj)!r}")


def dumps(obj: Any, *, indent: bool = False) -> bytes:
    option = orjson.OPT_INDENT_2 if indent else 0
    return orjson.dumps(obj, default=_default, option=option)


# ---------- DESERIALIZATION ----------

def _restore(obj: Any):
    # bytes marker
    if isinstance(obj, dict) and obj.get("__type__") == "bytes":
        if obj.get("encoding") != "base64":
            raise ValueError("Unsupported bytes encoding")
        return base64.b64decode(obj["value"])

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
