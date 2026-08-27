from __future__ import annotations

import json
import socket
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable


@dataclass(slots=True)
class StateEngine:
    """Read-only IPC client for the transparent overlay presentation layer.

    This object intentionally does not duplicate the runtime state machine in
    ``nova.core.state``. It only queries the live IPC socket and translates raw
    responses into plain-English overlay text that is easier for a user to read.
    """

    project_root: Path
    socket_path: Path | None = None
    _callbacks: list[Callable[[str], None]] = field(default_factory=list)
    current_status: str = "Listening…"

    def __post_init__(self) -> None:
        self.socket_path = self.project_root / ".runtime" / "nova-cortex.sock"

    def subscribe(self, callback: Callable[[str], None]) -> None:
        if callback not in self._callbacks:
            self._callbacks.append(callback)

    def unsubscribe(self, callback: Callable[[str], None]) -> None:
        if callback in self._callbacks:
            self._callbacks.remove(callback)

    def _notify(self, status: str) -> str:
        self.current_status = status
        for callback in tuple(self._callbacks):
            callback(status)
        return status

    def from_ipc_response(self, raw_response: str) -> str:
        response = (raw_response or "").strip()
        if not response:
            return self._notify("Listening…")
        return self._notify(self._map_response(response))

    def request_status(self, command: str = "status") -> str:
        if self.socket_path is None or not self.socket_path.exists():
            return self._notify("Listening…")

        payload = json.dumps({"tool": command}) + "\n"
        try:
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
                sock.connect(str(self.socket_path))
                sock.sendall(payload.encode("utf-8"))
                data = sock.recv(65536)
        except (FileNotFoundError, OSError):
            return self._notify("Listening…")

        return self.from_ipc_response(data.decode("utf-8", errors="replace"))

    @staticmethod
    def _map_response(raw_response: str) -> str:
        lowered = raw_response.lower()

        if "error" in lowered:
            return "Need attention…"
        if "wake" in lowered or "status:running" in lowered or "ack:wake" in lowered:
            return "Listening…"
        if "llm_chat" in lowered or "thinking" in lowered or "response:" in lowered:
            return "Thinking…"
        if "firefox" in lowered or "browser" in lowered or "open" in lowered and "browser" in lowered:
            return "Opening Firefox…"
        if "read_file" in lowered or "list_directory" in lowered or "file" in lowered:
            return "Reviewing files…"
        if "write_file" in lowered or "save" in lowered:
            return "Saving file…"
        if "execute_command" in lowered:
            return "Running command…"
        if "memory" in lowered:
            return "Learning…"
        return "Ready"


if __name__ == "__main__":
    engine = StateEngine(project_root=Path("."))
    print(engine._map_response("ack:wake"))
    print(engine._map_response("response:hello from Nova"))
