from __future__ import annotations

import json
from dataclasses import dataclass

from nova.llm.schema import ToolCall


@dataclass(slots=True)
class LLMOutput:
    raw_text: str
    tool_call: ToolCall | None = None

    def render(self) -> str:
        text = self.raw_text.replace("\n", " ").strip()
        if self.tool_call is not None:
            return f"llm_output:tool={self.tool_call.tool} arguments={self.tool_call.to_json()} text={text}"
        return f"llm_output:text={text}"


@dataclass(slots=True)
class LLMOutputParser:
    def parse(self, raw_text: str) -> LLMOutput:
        stripped = raw_text.strip()
        tool_call = self._extract_tool_call(stripped)
        return LLMOutput(raw_text=stripped, tool_call=tool_call)

    def render_preview(self, raw_text: str) -> str:
        return self.parse(raw_text).render()

    def _extract_tool_call(self, raw_text: str) -> ToolCall | None:
        if not raw_text:
            return None

        decoder = json.JSONDecoder()
        for index, character in enumerate(raw_text):
            if character != "{":
                continue

            try:
                payload, _ = decoder.raw_decode(raw_text[index:])
            except json.JSONDecodeError:
                continue

            if isinstance(payload, dict) and "tool" in payload:
                return ToolCall.from_json(json.dumps(payload))

        return None
