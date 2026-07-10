from __future__ import annotations

from dataclasses import dataclass
from shutil import which

from nova.core.config import NovaConfig


@dataclass(slots=True)
class LLMEngine:
    config: NovaConfig

    def is_available(self) -> bool:
        if self.config.llm_provider == "ollama":
            return which("ollama") is not None

        if self.config.llm_provider == "llama.cpp":
            return which("llama-cli") is not None or which("llama-server") is not None

        return which(self.config.llm_provider) is not None

    def render_status(self) -> str:
        availability = "available" if self.is_available() else "unavailable"
        return (
            f"llm:provider={self.config.llm_provider} model={self.config.llm_model} "
            f"base_url={self.config.llm_base_url} state={availability}"
        )
