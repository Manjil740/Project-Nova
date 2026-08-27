from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from nova.shield.classifier import RiskClassifier


@dataclass(slots=True)
class ConsentDecision:
    approved: bool
    risk_tier: int
    reason: str
    command: str
    prompt: str

    def render(self) -> str:
        state = "approved" if self.approved else "denied"
        return (
            f"consent:{state} tier={self.risk_tier} reason={self.reason} "
            f"command={self.command}"
        )


class ConsentManager:
    """Consent gate for tool actions above the safe threshold.

    This is intentionally minimal and uses the existing IPC tool router as the
    enforcement point. The user sees exactly what action is being requested.
    """

    def __init__(self, auto_approve_tier_0: bool = True, auto_approve_tier_1: bool = False) -> None:
        self.auto_approve_tier_0 = auto_approve_tier_0
        self.auto_approve_tier_1 = auto_approve_tier_1

    def evaluate(self, tool: str, arguments: dict[str, Any] | None = None, user_choice: str | None = None) -> ConsentDecision:
        decision = RiskClassifier.classify(tool, arguments)
        command = str(arguments.get("command", arguments.get("path", ""))) if arguments else ""
        prompt = self._build_prompt(tool, command, decision.reason)

        if decision.risk_tier == 0 and self.auto_approve_tier_0:
            return ConsentDecision(True, decision.risk_tier, decision.reason, command, prompt)
        if decision.risk_tier == 1 and self.auto_approve_tier_1:
            return ConsentDecision(True, decision.risk_tier, decision.reason, command, prompt)

        if user_choice is None:
            return ConsentDecision(False, decision.risk_tier, decision.reason, command, prompt)

        approved = str(user_choice).strip().lower() in {"yes", "y", "allow", "approve", "true"}
        return ConsentDecision(approved, decision.risk_tier, decision.reason, command, prompt)

    @staticmethod
    def _build_prompt(tool: str, command: str, reason: str) -> str:
        if not command:
            command = tool
        return f"Allow Nova to {tool} with: {command} ? (reason={reason})"
