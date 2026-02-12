from dataclasses import dataclass
from enum import Enum
from typing import Any, FrozenSet, Mapping, Optional


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
    SMS_CODE = "sms_code"
    TELEGRAM_CODE = "telegram_code"
    VOICE_CODE = "voice_code"
    CALL_CONFIRMATION = "call_confirmation"
    
    
class RoutingStrategy(str, Enum):
    FAILOVER = "failover"
    PARALLEL = "parallel"
    SINGLE = "single"


@dataclass(frozen=True)
class VerificationProvider:
    id: str
    name: str
    supported_methods: FrozenSet[VerificationMethod]
    config: Mapping[str, Any]
    is_enabled: bool


@dataclass(frozen=True)
class RoutingPolicy:
    method: VerificationMethod
    strategy: RoutingStrategy


@dataclass(frozen=True)
class RoutingEntry:
    method: VerificationMethod
    provider_id: str
    priority: int
