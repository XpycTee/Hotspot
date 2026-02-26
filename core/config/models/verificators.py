from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import List, Optional


@dataclass(frozen=True)
class SenderConfig:
    """
    External message sender configuration (SMS, HTTP API, etc).
    """

    type: str
    url: Optional[str] = None
    api_key: Optional[str] = None

    @property
    def params(self):
        if self.url is not None:
            return {'url': self.url}
        if self.api_key is not None:
            return {'api_key': self.api_key}
        return {}


@dataclass(frozen=True)
class CallcheckConfig:
    """

    """

    type: str
    call_phone: Optional[str] = None
    api_key: Optional[str] = None

    @property
    def params(self):
        if self.call_phone is not None:
            return {'call_phone': self.call_phone}
        if self.api_key is not None:
            return {'api_key': self.api_key}
        return {}


class VerificationMethod(str, Enum):
    CODE = "code"
    CALL = "call"

class VProviderType(str, Enum):
    SMSRU = "smsru"
    ASTERISK = "asterisk"
    MIKROTIK = "mikrotik"
    HUAWEI = "huawei"
    DEBUG = "debug"

@dataclass
class VProvidersList:
    items: List[VerificationProvider]
    order: List[VProviderType]

@dataclass(frozen=True)
class VerificationProvider:
    type: VProviderType
    name: str
    enabled: bool
    fields: List[VProviderField]
    supported_methods: List[VerificationMethod]

@dataclass(frozen=True)
class VProviderField:
    name: str = "api_key"
    label: str = "API Key"
    type: str = "password"
    value: str = ""
