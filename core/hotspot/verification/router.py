from dataclasses import dataclass
from enum import Enum, auto
from typing import List
from core.config import get_config
from core.config.models.verificators import VProviderType, VerificationMethod, VerificationProvider
from core.hotspot.verification.api import CodeDeliveryProvider, DeliveryStatus
from core.hotspot.verification.api.asterisk import AsteriskConfirm
from core.hotspot.verification.api.debug import DebugCodeDelivery
from core.hotspot.verification.api.huawei import HuaweiSMSSender
from core.hotspot.verification.api.mikrotik import MikrotikSMSSender
from core.hotspot.verification.api.smsru import SMSRU


class VRouterStatus(Enum):
    VERIFIED = auto()
    SENDED = auto()
    FAILED = auto()
    ERROR = auto()


@dataclass
class VRouterResponse:
    status: VRouterStatus
    provider: VProviderType

    # Options
    request_id: str | None = None
    call_phone:  str | None = None
    error_message: str | None = None


class VerificationRouter:
    def __init__(self):
        config = get_config()
        self._call_order = []
        self._code_order = []
        self._available_methods = set()

        call_order: List[VerificationProvider] = []
        code_order: List[VerificationProvider] = []
        for v in config.verificators.items:
            if v.enabled:
                self._available_methods.update(v.supported_methods)
                if VerificationMethod.CALL in v.supported_methods:
                    call_order.append(v)
                if VerificationMethod.CODE in v.supported_methods:
                    code_order.append(v)
                
        order = {value: index for index, value in enumerate(config.verificators.order)}
        self._call_order = sorted(call_order, key=lambda x: order[x.type])
        self._code_order = sorted(code_order, key=lambda x: order[x.type])

    @property
    def available_methods(self) -> set:
        return self._available_methods

    def send_code(self, recipient: str, code: str) -> VRouterResponse | List[VRouterResponse]:
        failed = []
        for cfg in self._code_order:
            if cfg.type == VProviderType.SMSRU:
                sender = SMSRU(cfg.fields[0].value)
            elif cfg.type == VProviderType.ASTERISK:
                sender = AsteriskConfirm(cfg.fields[0].value)
            elif cfg.type == VProviderType.MIKROTIK:
                sender = MikrotikSMSSender(cfg.fields[0].value)
            elif cfg.type == VProviderType.HUAWEI:
                sender = HuaweiSMSSender(cfg.fields[0].value)
            elif cfg.type == VProviderType.DEBUG:
                sender = DebugCodeDelivery()

            resp = sender.send_code(recipient, code)
            if resp.status == DeliveryStatus.SENT:
                return VRouterResponse(
                    status=VRouterStatus.SENDED,
                    provider=cfg.type,
                )
            
            if resp.status == DeliveryStatus.FAILED:
                failed.append(VRouterResponse(
                    status=VRouterStatus.FAILED,
                    provider=cfg.type,
                    error_message=resp.error_message,
                ))

            if resp.status == DeliveryStatus.ERROR:
                failed.append(VRouterResponse(
                    status=VRouterStatus.ERROR,
                    provider=cfg.type,
                    error_message=resp.error_message,
                ))

            if cfg == self._code_order[-1]:
                return failed


    def start_confirm(self, phone: str) -> VRouterResponse:
        # TODO
        return VRouterResponse(
            status=VRouterStatus.SENDED,
            provider=VProviderType.DEBUG,
            request_id=1,
            call_phone=2,
        )

    def check_confirm(self, request_id: str) -> VRouterResponse:
        # TODO
        return VRouterResponse(
            status=VRouterStatus.SENDED,
            provider=VProviderType.DEBUG,
        )
