from __future__ import annotations

from dataclasses import dataclass, field

from nova.core.config import NovaConfig
from nova.core.platform import SystemProfile
from nova.core.state import CortexState
from nova.llm.client import LLMClient, LLMResponse
from nova.llm.output import LLMOutputParser
from nova.llm.prompts import build_system_prompt
from nova.llm.schema import ToolCall
from nova.tools.registry import ToolRouter


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
            parts.append(f"tools=[{' | '.join(safe_tools)}]")
        return " ".join(parts)


@dataclass(slots=True)
class Pipeline:
    """Orchestrates prompt → LLM → parse tool calls → execute tools → return response.

    This is the core execution loop for conversational interactions with Nova.
    """

    config: NovaConfig
    llm_client: LLMClient
    router: ToolRouter
    parser: LLMOutputParser = LLMOutputParser()
    conversation_history: list[ConversationTurn] = field(default_factory=list)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def execute_simple(self, user_input: str, state: CortexState | None = None, system_profile: SystemProfile | None = None) -> PipelineResult:
        """Execute a simple prompt without tool routing.

        Direct model response — no tool execution. Useful for simple Q&A.
        """
        system_prompt = build_system_prompt(state, system_profile)
        full_prompt = f"{system_prompt}\n\nUser: {user_input}\n\nAssistant:"
        response = self.llm_client.execute(full_prompt)

        if not response.available:
            return PipelineResult(
                response_text=f"[LLM unavailable: {response.output}]",
                raw_model_output=response.output,
            )

        return PipelineResult(
            response_text=response.output,
            raw_model_output=response.output,
        )

    def execute_with_tools(self, user_input: str, state: CortexState | None = None, system_profile: SystemProfile | None = None) -> PipelineResult:
        """Full pipeline: system prompt → LLM → parse tool calls → route → return.

        Handles tool-augmented conversations where the model may call tools.
        Falls back to plain text when no tool is detected.
        """
        # Build context with conversation history
        system_prompt = build_system_prompt(state, system_profile)
        history_block = self._build_history_block()
        full_prompt = (
            f"{system_prompt}\n\n"
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

        return PipelineResult(
            response_text=response_text,
            tool_results=tool_results,
            raw_model_output=raw_output,
        )

    def clear_history(self) -> None:
        """Clear conversation history."""
        self.conversation_history.clear()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _execute_tool(self, tool_call: ToolCall) -> str:
        """Execute a single tool call through the router."""
        # Reconstruct the message as the router expects it
        message = tool_call.to_json() if tool_call.arguments else tool_call.tool
        if tool_call.arguments and "path" in tool_call.arguments:
            message = f"{tool_call.tool} {tool_call.arguments['path']}"

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
