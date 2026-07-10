from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from nova.core.platform import SystemProfile


@dataclass(slots=True)
class CortexState:
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    event_count: int = 0
    last_event: str = "idle"

    def record_event(self, event_name: str) -> None:
        self.event_count += 1
        self.last_event = event_name or "idle"

    def render_status(self, system_profile: SystemProfile | None = None) -> str:
        started = self.started_at.isoformat()
        profile_bits = f" distro={system_profile.short_name()}" if system_profile is not None else ""
        return f"status:running started_at={started} events={self.event_count} last_event={self.last_event}{profile_bits}"