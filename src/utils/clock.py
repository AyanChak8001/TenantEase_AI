"""Consistent real and simulated application clocks."""

from dataclasses import dataclass
from datetime import date, datetime, time
from zoneinfo import ZoneInfo

from config.settings import APPLICATION_TIMEZONE


@dataclass(frozen=True)
class ApplicationClock:
    """Clock used for scheduling decisions and newly-created event timestamps."""

    current: datetime | None = None

    @classmethod
    def real(cls):
        return cls(datetime.now(ZoneInfo(APPLICATION_TIMEZONE)).replace(tzinfo=None))

    @classmethod
    def simulated(cls, simulated_date: date, hour: int = 12):
        return cls(datetime.combine(simulated_date, time(hour=hour)))

    def now(self) -> datetime:
        return self.current or ApplicationClock.real().now()

    def today(self) -> date:
        return self.now().date()
