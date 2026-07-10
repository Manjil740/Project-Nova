from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from nova.tools.file_ops import list_directory, read_file


@dataclass(slots=True)
class ToolRouter:
    project_root: Path | None = None

    def dispatch(self, message: str) -> str:
        command, argument = self._split(message)

        if command in {"", "wake", "ping"}:
            return f"ack:{command or 'wake'}\n"

        if command == "list_directory":
            target = self._resolve(argument)
            return list_directory(target) + "\n"

        if command == "read_file":
            target = self._resolve(argument)
            return read_file(target) + "\n"

        return f"error:unknown_tool:{command}\n"

    def _split(self, message: str) -> tuple[str, str]:
        parts = message.split(maxsplit=1)
        if not parts:
            return "", ""

        command = parts[0].strip()
        argument = parts[1].strip() if len(parts) > 1 else ""
        return command, argument

    def _resolve(self, raw_path: str) -> Path:
        base_path = self.project_root or Path.cwd()
        if not raw_path:
            return base_path

        candidate_path = Path(raw_path).expanduser()
        if candidate_path.is_absolute():
            return candidate_path

        return base_path / candidate_path