from __future__ import annotations

import json
from dataclasses import dataclass

from nova.llm.schema import ToolCall


@dataclass(slots=True)
class LLMOutput:
    raw_text: str
    tool_call: ToolCall | None = None

    def render(self) -> str:
        # Rendered output is line-safe for IPC transports and logs.
        text = self.raw_text.replace("\n", " ").strip()
        if self.tool_call is not None:
            arguments_json = json.dumps(self.tool_call.arguments, sort_keys=True)
            return f"llm_output:tool={self.tool_call.tool} arguments={arguments_json} text={text}"
        return f"llm_output:text={text}"


@dataclass(slots=True)
class LLMOutputParser:
    """Extracts a tool envelope from model output when present.

    The parser scans for the first decodable JSON object with a 'tool' field
    so it can handle model responses that wrap JSON with extra prose.
    """

    def parse(self, raw_text: str) -> LLMOutput:
        stripped = raw_text.strip()
        tool_call = self._extract_tool_call(stripped)
        return LLMOutput(raw_text=stripped, tool_call=tool_call)

    def render_preview(self, raw_text: str) -> str:
        return self.parse(raw_text).render()

    def _extract_tool_call(self, raw_text: str) -> ToolCall | None:
        if not raw_text:
            return None

        # Scan left-to-right and decode the first valid JSON object containing
        # a `tool` key. This tolerates surrounding model prose such as:
        # "Sure, here is the call: { ... }".
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
