from __future__ import annotations

from pathlib import Path


def list_directory(target: Path) -> str:
    if not target.exists():
        return f"error:missing:{target}"

    if not target.is_dir():
        return f"error:not_directory:{target}"

    entries = sorted(child.name for child in target.iterdir())
    return "\n".join(entries) if entries else "(empty)"


def read_file(target: Path) -> str:
    if not target.exists():
        return f"error:missing:{target}"

    if not target.is_file():
        return f"error:not_file:{target}"

    return target.read_text(encoding="utf-8", errors="replace")
