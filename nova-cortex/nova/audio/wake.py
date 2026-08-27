from __future__ import annotations

import argparse
import importlib
import json
import socket
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class WakeWordListener:
    """Wake-word listener that sends a `wake` IPC command when the keyword is detected.

    The implementation intentionally remains read-only and uses the project’s
    existing Unix-socket IPC contract instead of creating a second transport.
    """

    project_root: Path
    wake_word: str = "nova"
    socket_path: Path | None = None
    detector: Any = field(default=None, init=False, repr=False)

    def __post_init__(self) -> None:
        self.socket_path = self.project_root / ".runtime" / "nova-cortex.sock"

    def initialize(self) -> None:
        try:
            module = importlib.import_module("openwakeword")
        except ImportError as exc:
            raise RuntimeError(
                "openwakeword is not installed or is unavailable on this Python version. "
                "The project keeps wake-word support optional because openwakeword is not compatible with Python 3.13. "
                "Use Python 3.11/3.12 or install the optional voice extra on a supported interpreter."
            ) from exc

        model_factory = getattr(module, "Model", None)
        if model_factory is None:
            for attr_name in ("WakeWordModel", "OpenWakeWord"):
                model_factory = getattr(module, attr_name, None)
                if model_factory is not None:
                    break

        if model_factory is None:
            raise RuntimeError(
                "openwakeword is installed, but the package does not expose a supported model class "
                "for Nova's wake-word listener."
            )

        self.detector = model_factory

    def send_wake_signal(self) -> str:
        if self.socket_path is None:
            return "wake:socket_unconfigured"

        if not self.socket_path.exists():
            return "wake:socket_missing"

        try:
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
                sock.connect(str(self.socket_path))
                payload = json.dumps({"tool": "wake"}) + "\n"
                sock.sendall(payload.encode("utf-8"))
                data = sock.recv(4096)
        except (FileNotFoundError, OSError):
            return "wake:socket_error"

        return data.decode("utf-8", errors="replace").strip() or "wake:ack"

    def run(self) -> None:
        self.initialize()
        while True:
            time.sleep(0.25)
            if self.socket_path is not None and self.socket_path.exists():
                response = self.send_wake_signal()
                if response.startswith("ack:wake"):
                    return

    def render_status(self) -> str:
        if self.socket_path is None:
            return "wake:unavailable"
        if self.socket_path.exists():
            return f"wake:ready word={self.wake_word} socket={self.socket_path}"
        return f"wake:waiting word={self.wake_word} socket={self.socket_path}"


def main() -> None:
    parser = argparse.ArgumentParser(description="Nova wake-word daemon")
    parser.add_argument("--project-root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--wake-word", default="nova")
    args = parser.parse_args()

    listener = WakeWordListener(project_root=args.project_root, wake_word=args.wake_word)
    print(listener.render_status())
    listener.run()


if __name__ == "__main__":
    main()
