from dataclasses import dataclass
from datetime import timedelta


@dataclass(frozen=True)
class HotspotUserConfig:
    """
    Per-user hotspot configuration.
    """

    password: str
    delay: timedelta


@dataclass
class HotspotConfig:
    """
    Hotspot runtime configuration.
    """

    online_timeout: timedelta
    staff: HotspotUserConfig
    guest: HotspotUserConfig

    def get_delay(self, is_staff: bool) -> timedelta:
        if is_staff:
            return self.staff.delay
        return self.guest.delay