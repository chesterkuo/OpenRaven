from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


def _env(key: str, default: str) -> str:
    """Read env var, return default if unset or empty."""
    return os.environ.get(key, "") or default


@dataclass
class RavenConfig:
    """Configuration for an OpenRaven knowledge base."""

    working_dir: Path
    llm_provider: str = field(default_factory=lambda: _env("OPENRAVEN_LLM_PROVIDER", "gemini"))
    llm_model: str = field(default_factory=lambda: _env("OPENRAVEN_LLM_MODEL", "gemini-2.5-flash"))
    wiki_llm_model: str = field(default_factory=lambda: _env("OPENRAVEN_WIKI_MODEL", "gemini-2.5-flash"))
    embedding_model: str = field(default_factory=lambda: _env("OPENRAVEN_EMBEDDING_MODEL", "text-embedding-004"))
    ollama_base_url: str = field(default_factory=lambda: _env("OPENRAVEN_OLLAMA_URL", "http://localhost:11434"))
    gemini_api_key: str = field(default_factory=lambda: os.environ.get("GEMINI_API_KEY", ""))
    anthropic_api_key: str = field(default_factory=lambda: os.environ.get("ANTHROPIC_API_KEY", ""))
    api_host: str = "127.0.0.1"
    api_port: int = 8741

    def __post_init__(self) -> None:
        self.working_dir = Path(self.working_dir).expanduser().resolve()
        self.working_dir.mkdir(parents=True, exist_ok=True)

    @property
    def llm_api_key(self) -> str:
        """Return the API key for the active provider (empty for Ollama)."""
        if self.llm_provider == "ollama":
            return ""
        return self.gemini_api_key

    @property
    def db_path(self) -> Path:
        return self.working_dir / "openraven.db"

    @property
    def lightrag_dir(self) -> Path:
        return self.working_dir / "lightrag_data"

    @property
    def wiki_dir(self) -> Path:
        return self.working_dir / "wiki"

    @property
    def ingestion_dir(self) -> Path:
        return self.working_dir / "ingested"
