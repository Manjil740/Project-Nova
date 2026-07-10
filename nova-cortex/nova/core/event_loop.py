from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path

from nova.core.ipc_server import IpcServer
from nova.core.platform import SystemProfile
from nova.core.state import CortexState


@dataclass(slots=True)
class CortexApp:
    project_root: Path

    def __post_init__(self) -> None:
        self.socket_path = self.project_root / ".runtime" / "nova-cortex.sock"

    async def run(self) -> None:
        self.socket_path.parent.mkdir(parents=True, exist_ok=True)
        state = CortexState()
        system_profile = SystemProfile.detect()
        server = IpcServer(self.socket_path, self.project_root, state, system_profile)
        await server.start()
        print(f"IPC listener active at {self.socket_path}")

        try:
            await asyncio.Event().wait()
        finally:
            await server.stop()
