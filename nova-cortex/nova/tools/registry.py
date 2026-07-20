from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from nova.core.config import NovaConfig
from nova.core.state import CortexState
from nova.core.platform import SystemProfile
from nova.core.report import RuntimeReport
from nova.core.events import EventBus, Event
from nova.llm.engine import LLMEngine
from nova.llm.client import LLMClient
from nova.llm.prompts import build_system_prompt
from nova.llm.schema import ToolCall
from nova.llm.pipeline import Pipeline
from nova.tools.file_ops import list_directory, read_file
from nova.memory.vector_db import VectorDB
from nova.memory.embeddings import Embeddings
from nova.memory.habit_tracker import HabitTracker


@dataclass(slots=True)
class ToolRouter:
    """Single entry point for IPC command dispatch.

    Keep this class deterministic and side-effect-light so later agents can
    safely add higher-risk tools (bash, network, system actions) behind the
    same routing surface.

        IPC command contract (current):
        - Incoming payload is a single line from the Unix socket.
        - Payload may be either plain text (`tool arg`) or JSON (`{"tool": ...}`).
        - Every dispatch result must return one trailing newline so simple clients
            can read responses with a single `readline()` call.

        Extension guideline:
        - Add new command branches in `dispatch()`.
        - Prefer explicit `*_unavailable` responses over exceptions.
        - Record state events only for meaningful runtime actions.
        - Keep path-based operations routed through `_resolve()`.
    """

    project_root: Path | None = None
    state: CortexState | None = None
    system_profile: SystemProfile | None = None
    config: NovaConfig | None = None
    llm_engine: LLMEngine | None = None
    llm_client: LLMClient | None = None
    pipeline: Pipeline | None = None
    vector_db: VectorDB | None = None
    embeddings: Embeddings | None = None
    habit_tracker: HabitTracker | None = None

    def dispatch(self, message: str) -> str:
        # The socket protocol is line-based text. Parse once and route by name.
        tool_call = self._parse(message)
        command = tool_call.tool
        argument = tool_call.arguments.get("path", "")

        # Liveness + lightweight status commands.
        if command in {"", "wake", "ping"}:
            if self.state is not None:
                self.state.record_event(command or "wake")
            return f"ack:{command or 'wake'}\n"

        if command == "status":
            if self.state is not None:
                return self.state.render_status(self.system_profile) + "\n"
            return "status:unavailable\n"

        if command == "system_info":
            if self.system_profile is not None:
                return self.system_profile.render() + "\n"
            return "system:unknown\n"

        if command == "system_prompt":
            return build_system_prompt(self.state, self.system_profile) + "\n"

        if command == "config_status":
            if self.config is not None:
                return self.config.render() + "\n"
            return "config:unavailable\n"

        if command == "llm_status":
            if self.llm_engine is not None:
                return self.llm_engine.render_status() + "\n"
            return "llm:unavailable\n"

        # LLM bridge commands
        if command == "llm_request_preview":
            if self.llm_client is not None:
                prompt = argument or build_system_prompt(self.state, self.system_profile)
                return self.llm_client.render_preview(prompt) + "\n"
            return "llm_request:unavailable\n"

        if command == "llm_execute_preview":
            if self.llm_client is not None:
                prompt = argument or build_system_prompt(self.state, self.system_profile)
                return self.llm_client.render_execution_preview(prompt) + "\n"
            return "llm_execute:unavailable\n"

        if command == "llm_execute":
            if self.llm_client is not None:
                prompt = argument or build_system_prompt(self.state, self.system_profile)
                response = self.llm_client.execute(prompt)
                if self.state is not None:
                    self.state.record_event(command)
                self._publish_tool_executed(command, prompt[:50])
                return response.render() + "\n"
            return "llm_execute:unavailable\n"

        if command == "llm_response_preview":
            if self.llm_client is not None:
                raw_text = argument or ""
                if not raw_text:
                    return "llm_response:missing_input\n"
                return self.llm_client.render_response_preview(raw_text) + "\n"
            return "llm_response:unavailable\n"

        # === Conversational Chat ===
        if command == "llm_chat":
            if self.pipeline is not None:
                if not argument:
                    return "llm_chat:missing_input\n"
                result = self.pipeline.execute_with_tools(
                    user_input=argument,
                    state=self.state,
                    system_profile=self.system_profile,
                )
                if self.state is not None:
                    self.state.record_event(command)
                self._publish_tool_executed(command, argument)
                return result.render() + "\n"
            return "llm_chat:unavailable\n"

        if command == "llm_chat_simple":
            if self.pipeline is not None:
                if not argument:
                    return "llm_chat:missing_input\n"
                result = self.pipeline.execute_simple(
                    user_input=argument,
                    state=self.state,
                    system_profile=self.system_profile,
                )
                if self.state is not None:
                    self.state.record_event(command)
                self._publish_tool_executed(command, argument)
                return result.render() + "\n"
            return "llm_chat:unavailable\n"

        if command == "llm_chat_clear":
            if self.pipeline is not None:
                self.pipeline.clear_history()
                return "llm_chat:history_cleared\n"
            return "llm_chat:unavailable\n"

        if command == "runtime_report":
            report = RuntimeReport(
                state=self.state,
                system_profile=self.system_profile,
                config=self.config,
                llm_engine=self.llm_engine,
            )
            return report.render().replace("\n", " | ") + "\n"

        # === Memory Commands ===
        if command == "memory_status":
            return self._memory_status() + "\n"

        if command == "memory_store":
            return self._memory_store(argument, tool_call.arguments) + "\n"

        if command == "memory_search":
            return self._memory_search(argument, tool_call.arguments) + "\n"

        if command == "memory_habits":
            return self._memory_habits() + "\n"

        if command == "memory_analyze":
            return self._memory_analyze() + "\n"

        # Workspace-bound read-only file helpers.
        if command == "list_directory":
            target = self._resolve(argument)
            if self.state is not None:
                self.state.record_event(command)
            self._publish_tool_executed(command, argument)
            return list_directory(target) + "\n"

        if command == "read_file":
            target = self._resolve(argument)
            if self.state is not None:
                self.state.record_event(command)
            self._publish_tool_executed(command, argument)
            return read_file(target) + "\n"

        return f"error:unknown_tool:{command}\n"

    # ------------------------------------------------------------------
    # Memory dispatch helpers
    # ------------------------------------------------------------------

    def _memory_status(self) -> str:
        """Return combined status of all memory components."""
        vdb_status = self.vector_db.render_status() if self.vector_db else "vector_db:unavailable"
        emb_status = self.embeddings.render_status() if self.embeddings else "embeddings:unavailable"
        ht_status = self.habit_tracker.render_status() if self.habit_tracker else "habit_tracker:unavailable"
        return f"memory_status: {vdb_status} | {emb_status} | {ht_status}"

    def _memory_store(self, text: str, args: dict[str, Any]) -> str:
        """Store a text in memory with embeddings.

        Required argument: 'path' (the text content) OR 'text' key.
        Optional: 'metadata' JSON string, 'id' custom ID.
        """
        if not self.vector_db or not self.embeddings:
            return "memory_store:unavailable (memory not initialized)"

        # Get the text from either 'path' (default from parser) or explicit 'text' key
        content = text or args.get("text", "")
        if not content:
            return "memory_store:missing_text (provide 'text' or use: memory_store <text>)"

        metadata_str = args.get("metadata", "{}")
        custom_id = args.get("id", "")

        try:
            metadata = json.loads(metadata_str) if isinstance(metadata_str, str) else {}
        except json.JSONDecodeError:
            metadata = {"source": "user_input"}

        import time
        doc_id = custom_id or f"mem_{int(time.time() * 1000)}_{hash(content) & 0xFFFFFF}"

        try:
            # Generate embedding
            embedding = self.embeddings.embed(content)

            # Store in vector DB
            self.vector_db.add_documents(
                ids=[doc_id],
                documents=[content],
                embeddings=[embedding],
                metadatas=[metadata],
            )

            # Log to habit tracker
            if self.habit_tracker:
                self.habit_tracker.log_command(
                    command="memory_store",
                    arguments=content[:50],
                    success=True,
                )

            # Publish event
            EventBus.get_instance().publish(
                Event("memory:stored", {"id": doc_id, "text": content[:100], "metadata": metadata})
            )

            if self.state is not None:
                self.state.record_event("memory_store")

            return f"memory_store:stored id={doc_id}"

        except Exception as exc:
            return f"memory_store:error {exc}"

    def _memory_search(self, query: str, args: dict[str, Any]) -> str:
        """Search memory for similar texts.

        Required argument: 'path' (the query text) OR 'text' key.
        Optional: 'n_results' (int, default 5), 'where' (JSON filter).
        """
        if not self.vector_db or not self.embeddings:
            return "memory_search:unavailable (memory not initialized)"

        query_text = query or args.get("text", "")
        if not query_text:
            return "memory_search:missing_query"

        n_results = int(args.get("n_results", "5"))
        where_str = args.get("where", "")
        where_filter = None
        if where_str:
            try:
                where_filter = json.loads(where_str)
            except json.JSONDecodeError:
                pass

        try:
            # Generate query embedding
            query_embedding = self.embeddings.embed(query_text)

            # Search vector DB
            results = self.vector_db.similarity_search(
                query_embeddings=[query_embedding],
                n_results=n_results,
                where=where_filter,
            )

            if not results:
                return "memory_search:no_results"

            # Format results
            output_parts = ["memory_search:results"]
            for i, r in enumerate(results):
                doc = r.get("document", "")
                dist = r.get("distance", 0)
                meta = r.get("metadata", {})
                doc_id = r.get("id", "")
                # Truncate long docs
                doc_display = doc[:100] + "..." if len(doc) > 100 else doc
                output_parts.append(
                    f"[{i + 1}] id={doc_id} dist={dist:.4f} meta={meta} text={doc_display}"
                )

            if self.state is not None:
                self.state.record_event("memory_search")

            return " | ".join(output_parts)

        except Exception as exc:
            return f"memory_search:error {exc}"

    def _memory_habits(self) -> str:
        """Get habit tracker status and recent patterns."""
        if not self.habit_tracker:
            return "memory_habits:unavailable (habit tracker not initialized)"

        try:
            patterns = self.habit_tracker.analyze_patterns()
            stats = self.habit_tracker.get_command_stats(days=7)
            suggestions = self.habit_tracker.get_suggestions(max_suggestions=3)

            parts = [f"memory_habits: total_commands={stats.get('total_commands', 0)}"]

            if patterns:
                top_patterns = sorted(patterns, key=lambda p: p.confidence, reverse=True)[:5]
                for p in top_patterns:
                    parts.append(
                        f"pattern:cmd={p.command_type} freq={p.frequency}/day "
                        f"hour={p.typical_hour}h conf={p.confidence}"
                    )

            if suggestions:
                for s in suggestions:
                    parts.append(f"suggestion:{s.suggestion_type} msg={s.message}")

            if self.state is not None:
                self.state.record_event("memory_habits")

            return " | ".join(parts)

        except Exception as exc:
            return f"memory_habits:error {exc}"

    def _memory_analyze(self) -> str:
        """Run full memory analysis and return summary."""
        if not self.habit_tracker:
            return "memory_analyze:unavailable"

        try:
            analysis = self.habit_tracker.run_weekly_analysis()
            summary = analysis.get("summary", "Analysis complete.")
            return f"memory_analyze: patterns={analysis.get('patterns_detected', 0)} suggestions={analysis.get('suggestions_generated', 0)} summary={summary}"
        except Exception as exc:
            return f"memory_analyze:error {exc}"

    def _publish_tool_executed(self, command, arguments="", success=True):
        """Publish a tool:executed event for habit tracking."""
        EventBus.get_instance().publish(
            Event("tool:executed", {
                "tool": command,
                "arguments": arguments,
                "success": success,
            })
        )

    # ------------------------------------------------------------------
    # Parsing & Resolution
    # ------------------------------------------------------------------

    def _parse(self, message: str) -> ToolCall:
        try:
            return ToolCall.from_message(message)
        except (ValueError, json.JSONDecodeError):
            return ToolCall(tool="", arguments={})

    def _resolve(self, raw_path: str) -> Path:
        """Resolve user-supplied paths while enforcing workspace boundaries."""

        base_path = self.project_root or Path.cwd()
        if not raw_path:
            return base_path.resolve()

        candidate_path = Path(raw_path).expanduser()
        if candidate_path.is_absolute():
            resolved_candidate = candidate_path.resolve(strict=False)
        else:
            resolved_candidate = (base_path / candidate_path).resolve(strict=False)

        resolved_base = base_path.resolve(strict=False)
        if resolved_candidate != resolved_base and resolved_base not in resolved_candidate.parents:
            raise ValueError(f"path_outside_workspace:{resolved_candidate}")

        return resolved_candidate
