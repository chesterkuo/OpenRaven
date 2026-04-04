from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class RavenConfig:
    """Configuration for an OpenRaven knowledge base."""

    working_dir: Path
    llm_provider: str = "gemini"
    llm_model: str = "gemini-2.5-flash"
    wiki_llm_model: str = "gemini-2.5-flash"
    # text-embedding-004 is Google's multilingual model — supports zh-TW + English.
    embedding_model: str = "text-embedding-004"
    gemini_api_key: str = field(default_factory=lambda: os.environ.get("GEMINI_API_KEY", ""))
    anthropic_api_key: str = field(default_factory=lambda: os.environ.get("ANTHROPIC_API_KEY", ""))
    api_host: str = "127.0.0.1"
    api_port: int = 8741

    def __post_init__(self) -> None:
        self.working_dir = Path(self.working_dir).expanduser().resolve()
        self.working_dir.mkdir(parents=True, exist_ok=True)

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
