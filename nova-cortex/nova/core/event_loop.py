from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path

from nova.core.config import NovaConfig
from nova.core.ipc_server import IpcServer
from nova.core.platform import SystemProfile
from nova.core.report import RuntimeReport
from nova.core.state import CortexState
from nova.llm.engine import LLMEngine
from nova.llm.client import LLMClient
from nova.llm.prompts import build_system_prompt
from nova.llm.pipeline import Pipeline
from nova.tools.registry import ToolRouter


@dataclass(slots=True)
class CortexApp:
    project_root: Path
    socket_path: Path | None = None

    def __post_init__(self) -> None:
        self.socket_path = self.project_root / ".runtime" / "nova-cortex.sock"

    async def run(self) -> None:
        self.socket_path.parent.mkdir(parents=True, exist_ok=True)
        config = NovaConfig.load(self.project_root)
        llm_engine = LLMEngine(config)
        llm_client = LLMClient(config)
        state = CortexState()
        system_profile = SystemProfile.detect()

        # Create the tool router
        router = ToolRouter(
            project_root=self.project_root,
            state=state,
            system_profile=system_profile,
            config=config,
            llm_engine=llm_engine,
            llm_client=llm_client,
        )

        # Create the pipeline with the router for tool execution
        pipeline = Pipeline(
            config=config,
            llm_client=llm_client,
            router=router,
        )

        # Attach pipeline back to router for IPC dispatch
        router.pipeline = pipeline

        server = IpcServer(
            self.socket_path,
            self.project_root,
            state,
            system_profile,
            config,
            llm_engine,
            llm_client,
            router,
        )
        await server.start()
        print(f"IPC listener active at {self.socket_path}")
        print(
            RuntimeReport(
                state=state,
                system_profile=system_profile,
                config=config,
                llm_engine=llm_engine,
            ).render()
        )
        print(llm_client.render_preview(build_system_prompt(state, system_profile)))

        try:
            await asyncio.Event().wait()
        finally:
            await server.stop()
