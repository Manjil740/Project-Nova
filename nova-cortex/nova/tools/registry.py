from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from nova.core.config import NovaConfig
from nova.core.state import CortexState
from nova.core.platform import SystemProfile
from nova.core.report import RuntimeReport
from nova.llm.engine import LLMEngine
from nova.llm.client import LLMClient
from nova.llm.prompts import build_system_prompt
from nova.llm.schema import ToolCall
from nova.tools.file_ops import list_directory, read_file


@dataclass(slots=True)
class ToolRouter:
    project_root: Path | None = None
    state: CortexState | None = None
    system_profile: SystemProfile | None = None
    config: NovaConfig | None = None
    llm_engine: LLMEngine | None = None
    llm_client: LLMClient | None = None

    def dispatch(self, message: str) -> str:
        tool_call = self._parse(message)
        command = tool_call.tool
        argument = tool_call.arguments.get("path", "")

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
                return response.render() + "\n"
            return "llm_execute:unavailable\n"

        if command == "llm_response_preview":
            if self.llm_client is not None:
                raw_text = argument or ""
                if not raw_text:
                    return "llm_response:missing_input\n"
                return self.llm_client.render_response_preview(raw_text) + "\n"
            return "llm_response:unavailable\n"

        if command == "runtime_report":
            report = RuntimeReport(
                state=self.state,
                system_profile=self.system_profile,
                config=self.config,
                llm_engine=self.llm_engine,
            )
            return report.render().replace("\n", " | ") + "\n"

        if command == "list_directory":
            target = self._resolve(argument)
            if self.state is not None:
                self.state.record_event(command)
            return list_directory(target) + "\n"

        if command == "read_file":
            target = self._resolve(argument)
            if self.state is not None:
                self.state.record_event(command)
            return read_file(target) + "\n"

        return f"error:unknown_tool:{command}\n"

    def _parse(self, message: str) -> ToolCall:
        try:
            return ToolCall.from_message(message)
        except (ValueError, json.JSONDecodeError):
            return ToolCall(tool="", arguments={})

    def _split(self, message: str) -> tuple[str, str]:
        parsed = self._parse(message)
        return parsed.tool, parsed.arguments.get("path", "")

    def _resolve(self, raw_path: str) -> Path:
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