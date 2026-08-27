from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


DEFAULT_LLM_PROVIDER = "ollama"
DEFAULT_LLM_MODEL = "qwen2.5-coder:3b"
DEFAULT_LLM_BASE_URL = "http://localhost:11434"
DEFAULT_EMBEDDING_MODEL = "nomic-embed-text"
DEFAULT_SANDBOX_ENABLED = True
DEFAULT_MEMORY_ENABLED = True
DEFAULT_CHROMA_DB_PATH = "~/.local/share/nova/chroma_db"
DEFAULT_EMBEDDING_BATCH_SIZE = 8
DEFAULT_DATA_DIR = "~/.local/share/nova"


@dataclass(slots=True)
class NovaConfig:
    llm_provider: str = DEFAULT_LLM_PROVIDER
    llm_model: str = DEFAULT_LLM_MODEL
    llm_base_url: str = DEFAULT_LLM_BASE_URL
    embedding_model: str = DEFAULT_EMBEDDING_MODEL
    sandbox_enabled: bool = DEFAULT_SANDBOX_ENABLED

    # Memory & storage fields
    memory_enabled: bool = DEFAULT_MEMORY_ENABLED
    chroma_db_path: str = DEFAULT_CHROMA_DB_PATH
    embedding_batch_size: int = DEFAULT_EMBEDDING_BATCH_SIZE
    data_dir: str = DEFAULT_DATA_DIR

    @classmethod
    def load(cls, project_root: Path) -> "NovaConfig":
        env_path = project_root / ".env"
        values = cls._parse_env_file(env_path)
        return cls(
            llm_provider=values.get("LLM_PROVIDER", DEFAULT_LLM_PROVIDER),
            llm_model=values.get("LLM_MODEL", DEFAULT_LLM_MODEL),
            llm_base_url=values.get("LLM_BASE_URL", DEFAULT_LLM_BASE_URL),
            embedding_model=values.get("EMBEDDING_MODEL", DEFAULT_EMBEDDING_MODEL),
            sandbox_enabled=values.get("SANDBOX_ENABLED", str(DEFAULT_SANDBOX_ENABLED)).lower() in {"1", "true", "yes", "on"},
            memory_enabled=values.get("MEMORY_ENABLED", str(DEFAULT_MEMORY_ENABLED)).lower() in {"1", "true", "yes", "on"},
            chroma_db_path=values.get("CHROMA_DB_PATH", DEFAULT_CHROMA_DB_PATH),
            embedding_batch_size=int(values.get("EMBEDDING_BATCH_SIZE", str(DEFAULT_EMBEDDING_BATCH_SIZE))),
            data_dir=values.get("DATA_DIR", DEFAULT_DATA_DIR),
        )

    @staticmethod
    def _parse_env_file(env_path: Path) -> dict[str, str]:
        if not env_path.exists():
            return {}

        values: dict[str, str] = {}
        for raw_line in env_path.read_text(encoding="utf-8", errors="replace").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            values[key.strip()] = value.strip()
        return values

    def render(self) -> str:
        sandbox_state = "enabled" if self.sandbox_enabled else "disabled"
        memory_state = "enabled" if self.memory_enabled else "disabled"
        return (
            f"config:provider={self.llm_provider} model={self.llm_model} "
            f"base_url={self.llm_base_url} embedding={self.embedding_model} "
            f"sandbox={sandbox_state} memory={memory_state} "
            f"chroma_db={self.chroma_db_path} batch={self.embedding_batch_size}"
        )
