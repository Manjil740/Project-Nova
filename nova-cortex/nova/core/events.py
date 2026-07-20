"""Simple in-process event bus for decoupled component communication.

Allows memory, tool, and shield modules to publish/subscribe to events
without direct import dependencies.

Usage:
    bus = EventBus.get_instance()
    
    # Subscribe
    def on_memory_update(event: Event):
        print(f"Memory updated: {event.data}")
    bus.subscribe("memory:updated", on_memory_update)
    
    # Publish  
    bus.publish(Event("memory:updated", {"key": "user_pref", "value": "dark_mode"}))
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass(slots=True)
class Event:
    """A single event with a type identifier and optional data payload."""

    type: str
    data: dict[str, Any] = field(default_factory=dict)


class EventBus:
    """Singleton in-process event bus.

    Thread-safe for asyncio contexts; not safe for multiprocessing.
    Use one bus instance per Cortex process.
    """

    _instance: EventBus | None = None

    def __new__(cls) -> EventBus:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._subscribers = {}
            cls._instance._event_log: list[Event] = []
            cls._instance._max_log = 100
        return cls._instance

    @classmethod
    def get_instance(cls) -> EventBus:
        return cls()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def subscribe(self, event_type: str, callback: Callable[[Event], None]) -> None:
        """Register a callback for a specific event type.

        Args:
            event_type: Dot-notation event type (e.g. "memory:updated", "tool:executed")
            callback: Function accepting an Event argument.
        """
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(callback)

    def unsubscribe(self, event_type: str, callback: Callable[[Event], None]) -> None:
        """Remove a previously registered callback."""
        if event_type in self._subscribers:
            self._subscribers[event_type] = [
                cb for cb in self._subscribers[event_type] if cb is not callback
            ]

    def publish(self, event: Event) -> None:
        """Publish an event to all subscribers of its type.

        Args:
            event: The Event instance to broadcast.
        """
        # Log the event
        self._event_log.append(event)
        if len(self._event_log) > self._max_log:
            self._event_log.pop(0)

        # Notify subscribers of exact type and wildcard "all"
        self._notify(event, event.type)
        if event.type != "all":
            self._notify(event, "all")

    def clear(self) -> None:
        """Clear all subscribers and event log."""
        self._subscribers.clear()
        self._event_log.clear()

    def recent_events(self, count: int = 10) -> list[Event]:
        """Return the most recent events from the log."""
        return self._event_log[-count:]

    def render_status(self) -> str:
        """Single-line status for IPC diagnostics."""
        subscriber_count = sum(len(cbs) for cbs in self._subscribers.values())
        return (
            f"event_bus:subscriber_count={subscriber_count} "
            f"logged_events={len(self._event_log)} "
            f"event_types={len(self._subscribers)}"
        )

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _notify(self, event: Event, event_type: str) -> None:
        for callback in self._subscribers.get(event_type, []):
            try:
                callback(event)
            except Exception:
                # Silently swallow subscriber errors to prevent one bad
                # subscriber from breaking the entire event chain.
                pass
