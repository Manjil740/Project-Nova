from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Sequence

from nova.llm.schema import ToolCall


@dataclass(slots=True)
class LLMOutput:
    raw_text: str
    tool_calls: list[ToolCall] = field(default_factory=list)

    def render(self) -> str:
        text = self.raw_text.replace("\n", " ").strip()
        if self.tool_calls:
            calls = "; ".join(
                f"tool={tc.tool} args={json.dumps(tc.arguments, sort_keys=True)}"
                for tc in self.tool_calls
            )
            return f"llm_output:calls=[{calls}] text={text}"
        return f"llm_output:text={text}"


@dataclass(slots=True)
class LLMOutputParser:
    """Extracts tool envelopes from model output when present.

    Supports multiple extraction strategies:
    1. JSON code blocks (```json { ... } ```)
    2. Raw JSON objects with a 'tool' field
    3. Falls back to plain text when no tool is found
    """

    def parse(self, raw_text: str) -> LLMOutput:
        stripped = raw_text.strip()
        if not stripped:
            return LLMOutput(raw_text="")

        tool_calls = self._extract_tool_calls(stripped)
        if tool_calls:
            # Strip the JSON tool call portions from the text to keep only prose
            cleaned = self._strip_tool_calls(stripped)
            return LLMOutput(raw_text=cleaned, tool_calls=tool_calls)
        return LLMOutput(raw_text=stripped, tool_calls=[])

    def render_preview(self, raw_text: str) -> str:
        return self.parse(raw_text).render()

    def _extract_tool_calls(self, raw_text: str) -> list[ToolCall]:
        """Extract all tool calls from the text using multiple strategies."""
        calls: list[ToolCall] = []

        # Strategy 1: Extract from markdown JSON code blocks
        calls.extend(self._extract_from_code_blocks(raw_text))

        # Strategy 2: Find raw JSON objects with 'tool' field
        if not calls:
            calls.extend(self._extract_raw_json_objects(raw_text))

        return calls

    def _extract_from_code_blocks(self, raw_text: str) -> list[ToolCall]:
        """Extract tool calls from ```json ... ``` blocks."""
        calls: list[ToolCall] = []
        pattern = r"```(?:json)?\s*\n?([\s\S]*?)```"
        for match in re.finditer(pattern, raw_text):
            block_content = match.group(1).strip()
            if not block_content:
                continue
            try:
                data = json.loads(block_content)
            except json.JSONDecodeError:
                continue
            call = self._dict_to_tool_call(data)
            if call is not None:
                calls.append(call)
                continue
            # Check for array of tool calls
            if isinstance(data, list):
                for item in data:
                    c = self._dict_to_tool_call(item)
                    if c is not None:
                        calls.append(c)
        return calls

    def _extract_raw_json_objects(self, raw_text: str) -> list[ToolCall]:
        """Scan for raw JSON objects with a 'tool' field."""
        calls: list[ToolCall] = []
        decoder = json.JSONDecoder()
        for index, character in enumerate(raw_text):
            if character != "{":
                continue
            try:
                payload, _ = decoder.raw_decode(raw_text[index:])
            except json.JSONDecodeError:
                continue
            if isinstance(payload, dict):
                call = self._dict_to_tool_call(payload)
                if call is not None:
                    calls.append(call)
        return calls

    def _dict_to_tool_call(self, data: dict) -> ToolCall | None:
        """Convert a dict to ToolCall if it has a valid 'tool' field."""
        if not isinstance(data, dict) or "tool" not in data:
            return None
        tool = str(data.get("tool", "")).strip()
        if not tool:
            return None
        raw_args = data.get("arguments", {}) or {}
        arguments: dict[str, str] = {}
        if isinstance(raw_args, dict):
            for key, value in raw_args.items():
                arguments[str(key)] = "" if value is None else str(value)
        return ToolCall(tool=tool, arguments=arguments)

    def _strip_tool_calls(self, raw_text: str) -> str:
        """Remove tool call JSON from the text, keeping only prose."""
        # Remove JSON code blocks
        cleaned = re.sub(r"```(?:json)?\s*\n?[\s\S]*?```", "", raw_text)
        # Remove raw JSON objects with 'tool' field
        decoder = json.JSONDecoder()
        parts: list[str] = []
        pos = 0
        while pos < len(cleaned):
            if cleaned[pos] == "{":
                try:
                    payload, end = decoder.raw_decode(cleaned[pos:])
                    if isinstance(payload, dict) and "tool" in payload:
                        pos += end
                        continue
                except json.JSONDecodeError:
                    pass
            parts.append(cleaned[pos])
            pos += 1
        return "".join(parts).strip()
