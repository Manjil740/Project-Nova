from __future__ import annotations

import json
from dataclasses import dataclass, field


@dataclass(slots=True)
class ToolCall:
    tool: str
    arguments: dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_message(cls, message: str) -> "ToolCall":
        text = message.strip()
        if text.startswith("{"):
            return cls.from_json(text)

        command, argument = cls._split_plaintext(text)
        return cls(tool=command, arguments={"path": argument} if argument else {})

    @classmethod
    def from_json(cls, payload: str) -> "ToolCall":
        data = json.loads(payload)
        tool = str(data.get("tool", "")).strip()
        raw_arguments = data.get("arguments", {})

        arguments: dict[str, str] = {}
        if isinstance(raw_arguments, dict):
            for key, value in raw_arguments.items():
                arguments[str(key)] = "" if value is None else str(value)

        return cls(tool=tool, arguments=arguments)

    def to_json(self) -> str:
        return json.dumps({"tool": self.tool, "arguments": self.arguments}, sort_keys=True)

    @staticmethod
    def _split_plaintext(message: str) -> tuple[str, str]:
        parts = message.split(maxsplit=1)
        if not parts:
            return "", ""

        command = parts[0].strip()
        argument = parts[1].strip() if len(parts) > 1 else ""
        return command, argument
