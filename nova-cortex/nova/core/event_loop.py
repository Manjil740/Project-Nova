from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path

from nova.core.config import NovaConfig
from nova.core.ipc_server import IpcServer
from nova.core.platform import SystemProfile
from nova.core.report import RuntimeReport
from nova.core.state import CortexState
from nova.core.events import EventBus, Event
from nova.llm.engine import LLMEngine
from nova.llm.client import LLMClient
from nova.llm.prompts import build_system_prompt
from nova.llm.pipeline import Pipeline
from nova.tools.registry import ToolRouter
from nova.memory.vector_db import VectorDB
from nova.memory.embeddings import Embeddings
from nova.memory.habit_tracker import HabitTracker


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

        # ------------------------------------------------------------------
        # Create components (memory objects are created but NOT initialized yet)
        # ------------------------------------------------------------------
        vector_db = VectorDB(
            persist_directory=Path(config.chroma_db_path).expanduser(),
            embedding_dimension=768,
        )
        embeddings = Embeddings(
            model_name=config.embedding_model,
            batch_size=config.embedding_batch_size,
            base_url=config.llm_base_url,
        )
        habit_tracker = HabitTracker()

        # Create router (will get memory components after init)
        router = ToolRouter(
            project_root=self.project_root,
            state=state,
            system_profile=system_profile,
            config=config,
            llm_engine=llm_engine,
            llm_client=llm_client,
            vector_db=None,
            embeddings=None,
            habit_tracker=None,
        )

        # Create pipeline (will get memory components after init)
        pipeline = Pipeline(
            config=config,
            llm_client=llm_client,
            router=router,
            vector_db=None,
            embeddings=None,
            habit_tracker=None,
        )

        # Attach pipeline back to router for IPC dispatch
        router.pipeline = pipeline

        # Start IPC server FIRST so the socket is available immediately
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

        # ------------------------------------------------------------------
        # Initialize Memory Components (after socket is live)
        # ------------------------------------------------------------------
        memory_initialized = False
        if config.memory_enabled:
            try:
                vector_db.initialize()
                print("[Memory] VectorDB initialized.")
                embeddings.initialize()
                print("[Memory] Embeddings initialized.")
                habit_tracker.initialize()
                print("[Memory] HabitTracker initialized.")
                memory_initialized = True

                # Attach memory components to router and pipeline now
                router.vector_db = vector_db
                router.embeddings = embeddings
                router.habit_tracker = habit_tracker
                pipeline.vector_db = vector_db
                pipeline.embeddings = embeddings
                pipeline.habit_tracker = habit_tracker
            except Exception as exc:
                print(f"[Memory] WARNING: Memory initialization failed: {exc}")
                print("[Memory] Nova will continue without memory features.")

        # Subscribe habit tracker to event bus for automatic command logging
        if memory_initialized:
            event_bus = EventBus.get_instance()

            def on_tool_executed(event: Event) -> None:
                tool_name = event.data.get("tool", "unknown")
                args = event.data.get("arguments", "")
                success = event.data.get("success", True)
                duration = event.data.get("duration_ms", 0.0)
                habit_tracker.log_command(
                    command=tool_name,
                    arguments=str(args),
                    success=success,
                    duration_ms=duration,
                )

            event_bus.subscribe("tool:executed", on_tool_executed)
        print(
            RuntimeReport(
                state=state,
                system_profile=system_profile,
                config=config,
                llm_engine=llm_engine,
            ).render()
        )
        print(llm_client.render_preview(build_system_prompt(state, system_profile)))

        # Print memory status if initialized
        if memory_initialized:
            print(f"[Memory] {vector_db.render_status()}")
            print(f"[Memory] {embeddings.render_status()}")
            print(f"[Memory] {habit_tracker.render_status()}")

        try:
            await asyncio.Event().wait()
        finally:
            await server.stop()
