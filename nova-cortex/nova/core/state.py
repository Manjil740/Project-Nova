from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from nova.core.platform import SystemProfile


@dataclass(slots=True)
class CortexState:
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    event_count: int = 0
    last_event: str = "idle"

    # Memory-phase stats (pre-wired)
    memory_queries: int = 0
    memory_hits: int = 0
    tool_calls_executed: int = 0

    def record_event(self, event_name: str) -> None:
        self.event_count += 1
        self.last_event = event_name or "idle"

    def record_memory_query(self, hit: bool = False) -> None:
        self.memory_queries += 1
        if hit:
            self.memory_hits += 1

    def record_tool_call(self) -> None:
        self.tool_calls_executed += 1

    def render_status(self, system_profile: SystemProfile | None = None) -> str:
        started = self.started_at.isoformat()
        profile_bits = f" distro={system_profile.short_name()}" if system_profile is not None else ""
        return (
            f"status:running started_at={started} events={self.event_count} "
            f"last_event={self.last_event} tools={self.tool_calls_executed} "
            f"mem_queries={self.memory_queries} mem_hits={self.memory_hits}{profile_bits}"
        )

    # ------------------------------------------------------------------
    # Persistent save/load
    # ------------------------------------------------------------------

    def save(self, path: Path) -> None:
        """Persist current state to a JSON file."""
        data = {
            "started_at": self.started_at.isoformat(),
            "event_count": self.event_count,
            "last_event": self.last_event,
            "memory_queries": self.memory_queries,
            "memory_hits": self.memory_hits,
            "tool_calls_executed": self.tool_calls_executed,
        }
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> "CortexState":
        """Restore state from a JSON file, or return fresh state if missing."""
        if not path.exists():
            return cls()
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return cls(
                started_at=datetime.fromisoformat(data.get("started_at", datetime.now(timezone.utc).isoformat())),
                event_count=data.get("event_count", 0),
                last_event=data.get("last_event", "idle"),
                memory_queries=data.get("memory_queries", 0),
                memory_hits=data.get("memory_hits", 0),
                tool_calls_executed=data.get("tool_calls_executed", 0),
            )
        except (json.JSONDecodeError, KeyError, ValueError):
            return cls()
