from core.config import get_config


class VerificationRouter:
    def available_methods(self) -> set:
        config = get_config()
        available = {}
        for v in config.verificators.items:
            if v.enabled:
                available += set(v.supported_methods)
        return available
    
    def send_code(self, recipient: str, code: str):
        pass

    def start_confirm(self, phone: str):
        pass

    def check_confirm(self, request_id: str):
        pass
