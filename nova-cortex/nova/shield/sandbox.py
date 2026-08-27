from __future__ import annotations

import shutil
from dataclasses import dataclass


@dataclass(slots=True)
class SandboxResult:
    enabled: bool
    mechanism: str
    reason: str

    def render(self) -> str:
        return f"sandbox:enabled={str(self.enabled).lower()} mechanism={self.mechanism} reason={self.reason}"


class SandboxManager:
    """Sandbox manager for higher-risk command execution.

    This uses `bubblewrap` when available, which is a real Linux package for
    process isolation. The implementation is intentionally conservative and
    returns a safe disabled state if the mechanism is not installed.
    """

    def __init__(self, enabled: bool = True) -> None:
        self.enabled = enabled and shutil.which("bwrap") is not None

    def check(self) -> SandboxResult:
        if not self.enabled:
            return SandboxResult(False, "none", "sandbox_unavailable")
        return SandboxResult(True, "bubblewrap", "sandbox_ready")

    def render_status(self) -> str:
        result = self.check()
        return result.render()
