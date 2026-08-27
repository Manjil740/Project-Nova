from __future__ import annotations

from dataclasses import dataclass

from nova.core.config import NovaConfig
from nova.core.platform import SystemProfile
from nova.core.state import CortexState
from nova.llm.engine import LLMEngine
from nova.llm.prompts import build_system_prompt


@dataclass(slots=True)
class RuntimeReport:
    state: CortexState | None = None
    system_profile: SystemProfile | None = None
    config: NovaConfig | None = None
    llm_engine: LLMEngine | None = None

    def render(self) -> str:
        parts: list[str] = []

        if self.state is not None:
            parts.append(self.state.render_status(self.system_profile))

        if self.system_profile is not None:
            parts.append(self.system_profile.render())

        if self.config is not None:
            parts.append(self.config.render())

        if self.llm_engine is not None:
            parts.append(self.llm_engine.render_status())

        if self.state is not None or self.system_profile is not None:
            parts.append(build_system_prompt(self.state, self.system_profile))

        return "\n".join(parts) if parts else "runtime:unavailable"
