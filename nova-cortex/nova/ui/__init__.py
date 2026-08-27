"""UI layer for Nova's transparent Linux overlay and state presentation."""

from nova.ui.state_engine import StateEngine

try:
    from nova.ui.overlay import NovaOverlay
except ImportError:  # pragma: no cover - optional GUI dependency handled at runtime
    NovaOverlay = None  # type: ignore[assignment]

__all__ = ["StateEngine", "NovaOverlay"]
