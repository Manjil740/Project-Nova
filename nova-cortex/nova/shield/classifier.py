from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class RiskDecision:
    tool: str
    risk_tier: int
    reason: str
    safe: bool

    def render(self) -> str:
        state = "safe" if self.safe else "blocked"
        return f"risk:{state} tool={self.tool} tier={self.risk_tier} reason={self.reason}"


class RiskClassifier:
    """Classify tool requests into risk tiers for the Linux-only Nova runtime.

    Risk tiers are intentionally simple and transparent:
    - 0: safe local read-only actions
    - 1: writable or command execution that requires review
    - 2: destructive or high-impact system changes
    """

    @staticmethod
    def classify(tool: str, arguments: dict[str, Any] | None = None) -> RiskDecision:
        args = arguments or {}

        if tool in {"status", "system_info", "config_status", "llm_status", "runtime_report", "list_directory", "read_file", "memory_search", "memory_habits", "memory_status"}:
            return RiskDecision(tool=tool, risk_tier=0, reason="read_only", safe=True)

        if tool in {"write_file", "memory_store", "memory_analyze"}:
            return RiskDecision(
                tool=tool,
                risk_tier=1,
                reason="writes_local_data",
                safe=False,
            )

        if tool in {"execute_command", "llm_execute", "llm_chat"}:
            command = str(args.get("command", args.get("path", ""))).lower()
            if any(marker in command for marker in ("sudo", "rm ", "mkfs", "dd ", "chmod 777", "curl | bash", "apt install", "systemctl", "service ")):
                return RiskDecision(tool=tool, risk_tier=2, reason="high_impact_system_change", safe=False)
            return RiskDecision(tool=tool, risk_tier=1, reason="command_execution", safe=False)

        if tool in {"llm_execute_preview", "llm_request_preview"}:
            return RiskDecision(tool=tool, risk_tier=0, reason="preview_only", safe=True)

        return RiskDecision(tool=tool, risk_tier=1, reason="unknown_tool_requires_review", safe=False)
