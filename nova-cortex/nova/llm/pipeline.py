from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from nova.core.config import NovaConfig
from nova.core.platform import SystemProfile
from nova.core.state import CortexState
from nova.core.events import EventBus, Event
from nova.llm.client import LLMClient, LLMResponse
from nova.llm.output import LLMOutputParser
from nova.llm.prompts import build_system_prompt
from nova.llm.schema import ToolCall

if TYPE_CHECKING:
    from nova.tools.registry import ToolRouter
    from nova.memory.vector_db import VectorDB
    from nova.memory.embeddings import Embeddings
    from nova.memory.habit_tracker import HabitTracker


@dataclass(slots=True)
class ConversationTurn:
    """A single turn in a multi-turn conversation."""

    role: str  # "user" or "assistant"
    content: str


@dataclass(slots=True)
class PipelineResult:
    """Result from the execution pipeline."""

    response_text: str
    tool_results: list[str] = field(default_factory=list)
    raw_model_output: str = ""

    def render(self) -> str:
        parts = [f"response:{self.response_text}"]
        if self.tool_results:
            safe_tools = [t.replace("\n", " ").strip() for t in self.tool_results]
            parts.append(f"tools=[{" | ".join(safe_tools)}]")
        return " ".join(parts)


@dataclass(slots=True)
class Pipeline:
    """Orchestrates prompt → LLM → parse tool calls → execute tools → return response.

    This is the core execution loop for conversational interactions with Nova.
    Supports automatic memory context injection when VectorDB and Embeddings
    are provided, enabling the LLM to recall relevant past interactions and
    user preferences.
    """

    config: NovaConfig
    llm_client: LLMClient
    router: ToolRouter
    parser: LLMOutputParser = field(default_factory=LLMOutputParser)
    conversation_history: list[ConversationTurn] = field(default_factory=list)
    vector_db: Any | None = None  # VectorDB | None
    embeddings: Any | None = None  # Embeddings | None
    habit_tracker: Any | None = None  # HabitTracker | None
    _memory_context_used: bool = False

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def execute_simple(self, user_input: str, state: CortexState | None = None, system_profile: SystemProfile | None = None) -> PipelineResult:
        """Execute a simple prompt without tool routing.

        Direct model response — no tool execution. Useful for simple Q&A.
        Injects memory context when available to personalize responses.
        """
        system_prompt = build_system_prompt(state, system_profile)
        memory_context = self._build_memory_context(user_input)
        full_prompt = f"{system_prompt}\n\n{memory_context}User: {user_input}\n\nAssistant:"
        response = self.llm_client.execute(full_prompt)

        if not response.available:
            return PipelineResult(
                response_text=f"[LLM unavailable: {response.output}]",
                raw_model_output=response.output,
            )

        # Auto-store conversation turn in memory
        self._auto_store_memory(user_input, response.output)

        return PipelineResult(
            response_text=response.output,
            raw_model_output=response.output,
        )

    def execute_with_tools(self, user_input: str, state: CortexState | None = None, system_profile: SystemProfile | None = None) -> PipelineResult:
        """Full pipeline: system prompt → LLM → parse tool calls → route → return.

        Handles tool-augmented conversations where the model may call tools.
        Falls back to plain text when no tool is detected.
        Automatically injects relevant memory context into the prompt.
        """
        # Build context with conversation history + memory
        system_prompt = build_system_prompt(state, system_profile)
        memory_context = self._build_memory_context(user_input)
        history_block = self._build_history_block()
        full_prompt = (
            f"{system_prompt}\n\n"
            f"{memory_context}"
            f"{history_block}"
            f"User: {user_input}\n\n"
            f"Assistant:"
        )

        # Execute LLM
        response = self.llm_client.execute(full_prompt)
        if not response.available:
            return PipelineResult(
                response_text=f"[LLM unavailable: {response.output}]",
                raw_model_output=response.output,
            )

        raw_output = response.output

        # Parse tool calls from model output
        parsed = self.parser.parse(raw_output)
        tool_results: list[str] = []

        # Execute each tool call
        for tool_call in parsed.tool_calls:
            result = self._execute_tool(tool_call)
            tool_results.append(result)
            # Record tool result in conversation history
            self.conversation_history.append(
                ConversationTurn(role="assistant", content=f"[Tool {tool_call.tool}: {result}]")
            )

        # Determine response text
        response_text = parsed.raw_text if parsed.raw_text else raw_output
        if not response_text and tool_results:
            response_text = f"Executed {len(tool_results)} tool(s)."

        # Record user input and assistant response in history
        self.conversation_history.append(ConversationTurn(role="user", content=user_input))
        self.conversation_history.append(ConversationTurn(role="assistant", content=response_text))

        # Trim history to prevent context overflow (keep last 10 turns)
        if len(self.conversation_history) > 20:
            self.conversation_history = self.conversation_history[-20:]

        # Auto-store conversation turn in memory
        self._auto_store_memory(user_input, response_text)

        return PipelineResult(
            response_text=response_text,
            tool_results=tool_results,
            raw_model_output=raw_output,
        )

    def clear_history(self) -> None:
        """Clear conversation history."""
        self.conversation_history.clear()

    # ------------------------------------------------------------------
    # Memory Integration
    # ------------------------------------------------------------------

    def _build_memory_context(self, user_input: str) -> str:
        """Build relevant memory context from vector DB and habit tracker.

        Searches for semantically similar past interactions and recent
        patterns, then formats them as context for the LLM prompt.

        Returns:
            Formatted memory context string (empty if no memory available).
        """
        if not self.vector_db or not self.embeddings:
            return ""

        context_parts: list[str] = []
        self._memory_context_used = False

        try:
            # 1. Semantic memory search
            query_embedding = self.embeddings.embed(user_input)
            memories = self.vector_db.similarity_search(
                query_embeddings=[query_embedding],
                n_results=3,
            )

            if memories:
                relevant_memories = [
                    m for m in memories
                    if m.get("distance", 1.0) < 1.0  # Only reasonably similar
                ]
                if relevant_memories:
                    self._memory_context_used = True
                    memory_lines: list[str] = []
                    for m in relevant_memories:
                        doc = m.get("document", "")
                        meta = m.get("metadata", {})
                        source = meta.get("source", "past")
                        memory_lines.append(f"- [{source}] {doc[:150]}")
                    context_parts.append(
                        "Relevant context from memory:\n" + "\n".join(memory_lines)
                    )

            # 2. Habit-based context
            if self.habit_tracker and self.habit_tracker.is_initialized:
                recent_cmds = self.habit_tracker.get_recent_commands(hours=1)
                if len(recent_cmds) > 3:
                    cmd_types = [c["command"] for c in recent_cmds[:5]]
                    cmd_summary = ", ".join(set(cmd_types))
                    context_parts.append(
                        f"Recent activity: {cmd_summary}"
                    )

        except Exception:
            # Silently degrade — memory context is advisory, not critical
            pass

        if not context_parts:
            return ""

        return "Memory context:\n" + "\n".join(context_parts) + "\n\n"

    def _auto_store_memory(self, user_input: str, response: str) -> None:
        """Automatically store user interactions in memory for future retrieval.

        Stores the conversation turn as a memory entry with metadata about
        the interaction type.
        """
        if not self.vector_db or not self.embeddings:
            return

        try:
            import time

            # Don't store empty or trivial messages
            if len(user_input.strip()) < 3:
                return

            # Generate embedding for the user input
            embedding = self.embeddings.embed(user_input)

            doc_id = f"conv_{int(time.time() * 1000)}_{hash(user_input) & 0xFFFFFF}"

            # Determine interaction type for metadata
            interaction_type = "chat"
            if any(kw in user_input.lower() for kw in ["my name", "i am", "i'm", "call me"]):
                interaction_type = "user_info"
            elif any(kw in user_input.lower() for kw in ["remember", "don't forget", "save this"]):
                interaction_type = "explicit_memory"

            self.vector_db.add_documents(
                ids=[doc_id],
                documents=[f"User: {user_input}\nAssistant: {response[:200]}"],
                embeddings=[embedding],
                metadatas=[{
                    "source": interaction_type,
                    "timestamp": time.time(),
                    "type": "conversation",
                }],
            )

            # Publish event for habit tracking
            EventBus.get_instance().publish(
                Event("memory:stored", {
                    "id": doc_id,
                    "source": interaction_type,
                    "text": user_input[:100],
                })
            )

        except Exception:
            # Memory storage is best-effort — don't break conversation
            pass

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _execute_tool(self, tool_call: ToolCall) -> str:
        """Execute a single tool call through the router."""
        # Always use JSON format for tools with complex arguments
        # Plain text format only for simple path-based commands like list_directory/read_file
        if tool_call.arguments and len(tool_call.arguments) == 1 and "path" in tool_call.arguments:
            message = f"{tool_call.tool} {tool_call.arguments['path']}"
        elif tool_call.arguments:
            message = tool_call.to_json()
        else:
            message = tool_call.tool

        try:
            result = self.router.dispatch(message)
            return result.strip()
        except ValueError as exc:
            return f"error:{exc}"
        except Exception as exc:
            return f"error:tool_execution_failed:{exc}"

    def _build_history_block(self) -> str:
        """Build conversation history block for context injection."""
        if not self.conversation_history:
            return ""

        lines: list[str] = []
        for turn in self.conversation_history:
            if turn.role == "user":
                lines.append(f"User: {turn.content}")
            else:
                lines.append(f"Assistant: {turn.content}")
        return "\n".join(lines) + "\n\n"
