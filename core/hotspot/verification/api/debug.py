from dataclasses import dataclass
from core.config.models.verificators import VerificationMethod
from core.hotspot.verification.api import CallConfirmationProvider, CodeDeliveryProvider, ConfirmResult, ConfirmStatus, DeliveryStatus, SendCodeResult
from core.logging import get_logger


logger = get_logger('core.hotspot.verification.api.debug')

class DebugCodeDelivery(CodeDeliveryProvider):
    def __init__(self, name: str = "Debug Code Delivery Provider"):
        self.name = name
        logger.debug(f"{self.name} initialized")

    def send_code(self, phone: str, code: str) -> bool:
        logger.info(f"[{self.name}] send_code called: phone={phone}, code={code}")
        # Просто возвращаем True, как будто доставка прошла успешно
        return SendCodeResult(
            status=DeliveryStatus.SENT,
        )
    

@dataclass
class DebugCallSession:
    request_id: str
    phone: str
    verified: bool = False
    

class DebugCallConfirmation(CallConfirmationProvider):
    def __init__(self, name: str = "Debug Call Confirmation Provider"):
        self.name = name
        self._sessions: dict[str, DebugCallSession] = {}
        self._counter = 0
        logger.debug(f"{self.name} initialized")

    def start_verification(self, phone: str) -> str:
        self._counter += 1
        request_id = f"debug-{self._counter}"
        session = DebugCallSession(request_id=request_id, phone=phone)
        self._sessions[request_id] = session
        logger.info(f"[{self.name}] start_verification called: phone={phone}, request_id={request_id}")
        return ConfirmResult(
            status=ConfirmStatus.PENDING,
            request_id=request_id,
            call_phone="Debug",
        )

    def check_verification(self, request_id: str) -> bool:
        session = self._sessions.get(request_id)
        if not session:
            logger.warning(f"[{self.name}] check_verification: unknown request_id={request_id}")
            return ConfirmResult(
                status=ConfirmStatus.ERROR,
            )

        # Для дебага просто помечаем как verified после проверки
        session.verified = True
        logger.info(f"[{self.name}] check_verification: request_id={request_id}, verified={session.verified}")

        return ConfirmResult(
            status=ConfirmStatus.VERIFIED,
        )