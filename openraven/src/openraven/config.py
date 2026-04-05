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
    google_client_id: str = field(default_factory=lambda: os.environ.get("GOOGLE_CLIENT_ID", ""))
    google_client_secret: str = field(default_factory=lambda: os.environ.get("GOOGLE_CLIENT_SECRET", ""))
    database_url: str = field(default_factory=lambda: _env("DATABASE_URL", ""))
    graph_backend: str = field(default_factory=lambda: _env("GRAPH_BACKEND", "networkx"))
    neo4j_uri: str = field(default_factory=lambda: _env("NEO4J_URI", "bolt://localhost:7687"))
    neo4j_user: str = field(default_factory=lambda: _env("NEO4J_USER", "neo4j"))
    neo4j_password: str = field(default_factory=lambda: _env("NEO4J_PASSWORD", ""))
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
    def auth_enabled(self) -> bool:
        """Auth is enabled when DATABASE_URL is set."""
        return bool(self.database_url)

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

    @property
    def courses_dir(self) -> Path:
        return self.working_dir / "courses"

    @property
    def google_token_path(self) -> Path:
        return self.working_dir / "google_token.json"

    @property
    def otter_key_path(self) -> Path:
        return self.working_dir / "otter_api_key"

    @property
    def otter_api_key(self) -> str:
        """Load Otter.ai API key from file. Returns empty string if not found."""
        if not self.otter_key_path.exists():
            return ""
        return self.otter_key_path.read_text(encoding="utf-8").strip()
