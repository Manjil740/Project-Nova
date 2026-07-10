from __future__ import annotations

import asyncio
from pathlib import Path

from nova.tools.registry import ToolRouter


class IpcServer:
    def __init__(self, socket_path: Path, project_root: Path) -> None:
        self.socket_path = socket_path
        self._server: asyncio.AbstractServer | None = None
        self._router = ToolRouter(project_root=project_root)

    async def start(self) -> None:
        if self.socket_path.exists():
            self.socket_path.unlink()

        self._server = await asyncio.start_unix_server(
            self._handle_client,
            path=str(self.socket_path),
        )

    async def stop(self) -> None:
        if self._server is None:
            return

        self._server.close()
        await self._server.wait_closed()
        self._server = None

        if self.socket_path.exists():
            self.socket_path.unlink()

    async def _handle_client(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
    ) -> None:
        payload = await reader.readline()
        message = payload.decode("utf-8", errors="replace").strip()
        response = self._router.dispatch(message)
        writer.write(response.encode("utf-8"))
        await writer.drain()
        writer.close()
        await writer.wait_closed()