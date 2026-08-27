"""Storage manager for Nova Cortex data directories.

Manages the local filesystem layout for persistent data:
- `~/.local/share/nova/chroma_db/` — Vector database files
- `~/.local/share/nova/logs/` — Runtime and tool execution logs
- Project-local `data/` — Config-specific working data

All paths are lazily resolved and created on first access.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(slots=True)
class StorageManager:
    """Manages Nova's data directory layout on the local filesystem.

    Usage:
        storage = StorageManager()
        chroma_path = storage.chroma_path   # ~/.local/share/nova/chroma_db/
        log_path    = storage.log_path       # ~/.local/share/nova/logs/
    """

    base_dir: Path = field(
        default_factory=lambda: Path.home() / ".local" / "share" / "nova"
    )

    def __post_init__(self) -> None:
        self._ensure_dirs()

    # ------------------------------------------------------------------
    # Path properties — lazily created
    # ------------------------------------------------------------------

    @property
    def chroma_path(self) -> Path:
        return self.base_dir / "chroma_db"

    @property
    def log_path(self) -> Path:
        return self.base_dir / "logs"

    @property
    def data_path(self) -> Path:
        return self.base_dir / "data"

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def ensure(self) -> None:
        """Idempotent directory creation — safe to call on every startup."""
        self._ensure_dirs()

    def render_status(self) -> str:
        """Single-line status for IPC diagnostics."""
        chroma_ok = self.chroma_path.exists()
        logs_ok = self.log_path.exists()
        base_ok = self.base_dir.exists()
        return (
            f"storage:base={self.base_dir} "
            f"chroma={'ok' if chroma_ok else 'missing'} "
            f"logs={'ok' if logs_ok else 'missing'} "
            f"healthy={'yes' if (base_ok and chroma_ok and logs_ok) else 'no'}"
        )

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _ensure_dirs(self) -> None:
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.chroma_path.mkdir(parents=True, exist_ok=True)
        self.log_path.mkdir(parents=True, exist_ok=True)
        self.data_path.mkdir(parents=True, exist_ok=True)
