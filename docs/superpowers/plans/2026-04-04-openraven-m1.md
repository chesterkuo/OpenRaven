# OpenRaven M1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the complete OpenRaven M1: a 4-stage knowledge compilation pipeline (ingest → extract → graph → wiki), CLI tool, Python API server, and minimal Web UI — targeting engineers and financial analysts with mixed zh-TW/English documents.

**Architecture:** Two-service architecture: Python core engine (FastAPI) handles the knowledge pipeline (LangExtract + LightRAG + Docling), TypeScript frontend (Bun + Hono + React + Vite) provides the Web UI and proxies to the Python API. Multi-repo: `openraven` (Python core) and `openraven-ui` (TS frontend+backend). Cloud LLM APIs (Claude/Gemini) only for M1; Ollama deferred to M2.

**Tech Stack:** Python 3.12, LangExtract, LightRAG (lightrag-hku), Docling, NetworkX, NanoVectorDB, SQLite, FastAPI, Click; Bun, Hono, React, Vite, TypeScript.

**Key Decisions (from PRD review 2026-04-04):**
- Python core + TypeScript backend (two services, HTTP IPC)
- Multi-repo (4 repos, M1 focuses on openraven + openraven-ui)
- Neo4j as container for production (M1 uses NetworkX locally)
- Cloud API first (Claude/Gemini), Ollama in M2
- CLI + minimal Web UI for M1
- Alpha users: engineers + financial analysts
- Mixed zh-TW + English documents
- Include proactive discovery ("first surprise moment") in M1

---

## File Structure

### Repo 1: `openraven` (Python Core Engine — Apache 2.0)

```
openraven/
├── pyproject.toml
├── README.md
├── .github/
│   └── workflows/
│       └── ci.yml
├── src/openraven/
│   ├── __init__.py                    # Package version
│   ├── config.py                      # Configuration (API keys, paths, model selection)
│   ├── ingestion/
│   │   ├── __init__.py
│   │   ├── parser.py                  # Docling integration — parse PDF/DOCX/PPTX/XLSX/MD to text
│   │   └── hasher.py                  # SHA-256 file hashing for incremental updates
│   ├── extraction/
│   │   ├── __init__.py
│   │   ├── extractor.py              # LangExtract integration — entity extraction with source grounding
│   │   └── schemas/
│   │       ├── __init__.py
│   │       ├── base.py               # Base schema (generic knowledge extraction)
│   │       ├── engineering.py         # ADR, tech spec, architecture decision schemas
│   │       └── finance.py            # Research report, earnings call schemas
│   ├── graph/
│   │   ├── __init__.py
│   │   └── rag.py                    # LightRAG wrapper — init, insert, query, export
│   ├── wiki/
│   │   ├── __init__.py
│   │   └── compiler.py              # Wiki article generation from graph + source positions
│   ├── discovery/
│   │   ├── __init__.py
│   │   └── analyzer.py              # Proactive discovery — patterns, themes, similar items
│   ├── health/
│   │   ├── __init__.py
│   │   └── reporter.py             # Knowledge base health report (stats, coverage)
│   ├── pipeline.py                  # Orchestrates all 4 stages sequentially
│   ├── storage.py                   # SQLite metadata store (file records, processing state)
│   └── api/
│       ├── __init__.py
│       └── server.py               # FastAPI server — REST endpoints for TS backend
├── cli/
│   ├── __init__.py
│   └── main.py                     # `raven` CLI tool (init, add, ask, status, graph, export)
└── tests/
    ├── conftest.py                 # Shared fixtures (temp dirs, sample docs, mock LLM)
    ├── fixtures/
    │   ├── sample_en.md            # English test document (~500 words)
    │   └── sample_zh.md            # Traditional Chinese test document (~500 words)
    ├── test_ingestion.py
    ├── test_extraction.py
    ├── test_graph.py
    ├── test_wiki.py
    ├── test_discovery.py
    ├── test_health.py
    ├── test_pipeline.py
    ├── test_storage.py
    └── test_api.py
```

### Repo 2: `openraven-ui` (TypeScript Frontend + Backend)

```
openraven-ui/
├── package.json
├── tsconfig.json
├── vite.config.ts
├── .github/
│   └── workflows/
│       └── ci.yml
├── server/
│   ├── index.ts                    # Hono server entry point
│   ├── routes/
│   │   ├── ask.ts                  # POST /api/ask — proxy to Python core
│   │   ├── ingest.ts               # POST /api/ingest — file upload + proxy
│   │   ├── status.ts               # GET /api/status — knowledge base stats
│   │   └── discovery.ts            # GET /api/discovery — proactive insights
│   └── services/
│       └── core-client.ts          # HTTP client to Python FastAPI server
├── src/
│   ├── App.tsx                     # Root component with router
│   ├── main.tsx                    # Vite entry
│   ├── index.css                   # Tailwind base styles
│   ├── pages/
│   │   ├── AskPage.tsx             # Chat-style Q&A interface
│   │   ├── StatusPage.tsx          # Knowledge base health dashboard
│   │   └── IngestPage.tsx          # File upload / drag-drop
│   └── components/
│       ├── ChatMessage.tsx         # Single message bubble with source citations
│       ├── FileUploader.tsx        # Drag-and-drop file upload
│       ├── DiscoveryCard.tsx       # Proactive insight card
│       └── SourceCitation.tsx      # Clickable source reference
└── tests/
    ├── server/
    │   └── routes.test.ts
    └── components/
        └── ChatMessage.test.tsx
```

---

## Task 1: Python Project Scaffolding (`openraven` repo)

**Files:**
- Create: `openraven/pyproject.toml`
- Create: `openraven/src/openraven/__init__.py`
- Create: `openraven/src/openraven/config.py`
- Create: `openraven/tests/conftest.py`
- Create: `openraven/.github/workflows/ci.yml`

- [ ] **Step 1: Create the GitHub repo and clone it**

```bash
cd /home/ubuntu/source/OpenRaven
mkdir openraven && cd openraven
git init
```

- [ ] **Step 2: Create pyproject.toml with all dependencies**

```toml
# openraven/pyproject.toml
[project]
name = "openraven"
version = "0.1.0"
description = "AI-powered personal professional knowledge asset platform"
readme = "README.md"
license = "Apache-2.0"
requires-python = ">=3.12"
dependencies = [
    "langextract>=0.1.0",
    "lightrag-hku>=1.0.0",
    "docling>=2.0.0",
    "fastapi>=0.115.0",
    "uvicorn[standard]>=0.30.0",
    "click>=8.1.0",
    "anthropic>=0.40.0",
    "google-genai>=1.0.0",
    "httpx>=0.27.0",
    "pydantic>=2.0.0",
    "networkx>=3.0",
    "jinja2>=3.1.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.24.0",
    "pytest-cov>=5.0.0",
    "ruff>=0.7.0",
    "mypy>=1.11.0",
    "respx>=0.21.0",
]

[project.scripts]
raven = "cli.main:cli"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/openraven", "cli"]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]

[tool.ruff]
target-version = "py312"
line-length = 100

[tool.ruff.lint]
select = ["E", "F", "I", "N", "W", "UP"]
```

- [ ] **Step 3: Create config module**

```python
# openraven/src/openraven/config.py
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class RavenConfig:
    """Configuration for an OpenRaven knowledge base."""

    working_dir: Path
    llm_provider: str = "gemini"  # "gemini", "anthropic"
    llm_model: str = "gemini-2.5-flash"
    wiki_llm_model: str = "claude-sonnet-4-6"
    # text-embedding-004 is Google's multilingual model — supports zh-TW + English.
    # For local/self-hosted: use "bge-m3" or "multilingual-e5-large" via Ollama (M2).
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
```

- [ ] **Step 4: Create __init__.py**

```python
# openraven/src/openraven/__init__.py
"""OpenRaven — AI-powered personal professional knowledge asset platform."""

__version__ = "0.1.0"
```

- [ ] **Step 5: Create test conftest with shared fixtures**

```python
# openraven/tests/conftest.py
from __future__ import annotations

from pathlib import Path

import pytest

from openraven.config import RavenConfig


@pytest.fixture
def tmp_working_dir(tmp_path: Path) -> Path:
    """Provide a temporary working directory for tests."""
    wd = tmp_path / "test_kb"
    wd.mkdir()
    return wd


@pytest.fixture
def config(tmp_working_dir: Path) -> RavenConfig:
    """Provide a test RavenConfig pointing to a temp directory."""
    return RavenConfig(
        working_dir=tmp_working_dir,
        gemini_api_key="test-key",
        anthropic_api_key="test-key",
    )


SAMPLE_EN_TEXT = """
# Architecture Decision Record: Migrate to Event-Driven Architecture

## Status: Accepted

## Context
Our monolithic order processing system handles 50,000 orders/day but cannot scale beyond 80,000.
The team evaluated three approaches: horizontal scaling, CQRS, and event-driven architecture.

## Decision
We chose event-driven architecture using Apache Kafka because:
1. Decouples order intake from fulfillment processing
2. Enables independent scaling of consumer services
3. Provides natural audit trail via event log

## Consequences
- Positive: 5x throughput improvement in load tests
- Negative: Added operational complexity for Kafka cluster management
- Risk: Eventual consistency requires careful handling of order status queries
"""

SAMPLE_ZH_TEXT = """
# 投資研究報告：台灣半導體產業分析

## 摘要
台灣半導體產業在全球供應鏈中佔據關鍵地位。台積電（TSMC）在先進製程市場佔有率超過 90%。

## 關鍵發現
1. 先進封裝技術（CoWoS）產能將在 2026 年擴充 3 倍
2. AI 晶片需求推動營收年增率達 25%
3. 地緣政治風險促使客戶分散供應鏈

## 估值分析
目前本益比（P/E）為 22 倍，低於五年平均 25 倍。考慮 AI 需求成長，目標價上調 15%。

## 風險因素
- 中美貿易摩擦升級
- 先進製程良率低於預期
- 全球經濟衰退導致需求下滑
"""
```

- [ ] **Step 6: Create CI workflow**

```yaml
# openraven/.github/workflows/ci.yml
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install -e ".[dev]"
      - run: ruff check src/ cli/ tests/
      - run: pytest --cov=openraven -v
```

- [ ] **Step 7: Create .env.example for required API keys**

```bash
# openraven/.env.example
# Required for cloud LLM mode (M1 default):
GEMINI_API_KEY=your-gemini-api-key-here
ANTHROPIC_API_KEY=your-anthropic-api-key-here

# Optional: Override defaults
# OPENRAVEN_WORKING_DIR=~/my-knowledge
# OPENRAVEN_LLM_MODEL=gemini-2.5-flash
# OPENRAVEN_WIKI_MODEL=claude-sonnet-4-6
```

- [ ] **Step 8: Create directory structure and init files**

```bash
mkdir -p src/openraven/{ingestion,extraction/schemas,graph,wiki,discovery,health,api}
mkdir -p cli tests/fixtures
touch src/openraven/{ingestion,extraction,extraction/schemas,graph,wiki,discovery,health,api}/__init__.py
touch cli/__init__.py
```

- [ ] **Step 9: Install dependencies and verify**

```bash
pip install -e ".[dev]"
python -c "from openraven.config import RavenConfig; print('OK')"
```

- [ ] **Step 10: Commit**

```bash
git add -A
git commit -m "feat: scaffold openraven Python project with config and CI"
```

---

## Task 2: Document Ingestion Layer

**Files:**
- Create: `src/openraven/ingestion/parser.py`
- Create: `src/openraven/ingestion/hasher.py`
- Create: `src/openraven/storage.py`
- Create: `tests/test_ingestion.py`
- Create: `tests/test_storage.py`
- Create: `tests/fixtures/sample_en.md`
- Create: `tests/fixtures/sample_zh.md`

- [ ] **Step 1: Create test fixture files**

Write `tests/fixtures/sample_en.md` with the `SAMPLE_EN_TEXT` content from conftest.
Write `tests/fixtures/sample_zh.md` with the `SAMPLE_ZH_TEXT` content from conftest.

- [ ] **Step 2: Write failing tests for file hashing**

```python
# openraven/tests/test_ingestion.py
from pathlib import Path

from openraven.ingestion.hasher import compute_file_hash


def test_compute_file_hash_deterministic(tmp_path: Path) -> None:
    f = tmp_path / "test.txt"
    f.write_text("hello world")
    h1 = compute_file_hash(f)
    h2 = compute_file_hash(f)
    assert h1 == h2
    assert len(h1) == 64  # SHA-256 hex


def test_compute_file_hash_changes_on_content_change(tmp_path: Path) -> None:
    f = tmp_path / "test.txt"
    f.write_text("version 1")
    h1 = compute_file_hash(f)
    f.write_text("version 2")
    h2 = compute_file_hash(f)
    assert h1 != h2
```

- [ ] **Step 3: Run tests to verify they fail**

```bash
pytest tests/test_ingestion.py -v
```
Expected: FAIL — `ModuleNotFoundError: No module named 'openraven.ingestion.hasher'`

- [ ] **Step 4: Implement hasher**

```python
# openraven/src/openraven/ingestion/hasher.py
from __future__ import annotations

import hashlib
from pathlib import Path


def compute_file_hash(file_path: Path, algorithm: str = "sha256") -> str:
    """Compute hex digest hash of a file's contents."""
    h = hashlib.new(algorithm)
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()
```

- [ ] **Step 5: Run hash tests to verify they pass**

```bash
pytest tests/test_ingestion.py -v
```
Expected: PASS

- [ ] **Step 6: Write failing tests for document parser**

```python
# append to openraven/tests/test_ingestion.py
from openraven.ingestion.parser import parse_document, ParsedDocument


def test_parse_markdown_file(tmp_path: Path) -> None:
    md = tmp_path / "test.md"
    md.write_text("# Title\n\nSome content here.")
    result = parse_document(md)
    assert isinstance(result, ParsedDocument)
    assert "Title" in result.text
    assert "Some content here" in result.text
    assert result.source_path == md
    assert result.format == "md"


def test_parse_document_returns_metadata(tmp_path: Path) -> None:
    md = tmp_path / "report.md"
    md.write_text("# Report\n\nAnalysis of market trends.")
    result = parse_document(md)
    assert result.char_count > 0
    assert result.source_path.name == "report.md"
```

- [ ] **Step 7: Run tests to verify they fail**

```bash
pytest tests/test_ingestion.py::test_parse_markdown_file -v
```
Expected: FAIL — `ImportError`

- [ ] **Step 8: Implement document parser**

```python
# openraven/src/openraven/ingestion/parser.py
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from docling.document_converter import DocumentConverter


@dataclass
class ParsedDocument:
    """A document converted to plain text with metadata."""

    text: str
    source_path: Path
    format: str
    char_count: int


# Singleton converter — expensive to initialize
_converter: DocumentConverter | None = None


def _get_converter() -> DocumentConverter:
    global _converter
    if _converter is None:
        _converter = DocumentConverter()
    return _converter


def parse_url(url: str) -> ParsedDocument:
    """Parse a web URL into plain text using Jina Reader.

    Jina Reader converts web pages to clean Markdown via https://r.jina.ai/{url}.
    """
    import httpx

    response = httpx.get(
        f"https://r.jina.ai/{url}",
        headers={"Accept": "text/markdown"},
        timeout=30.0,
    )
    response.raise_for_status()
    text = response.text

    return ParsedDocument(
        text=text,
        source_path=Path(url),  # Store URL as path for traceability
        format="url",
        char_count=len(text),
    )


def parse_document(file_path: Path | str) -> ParsedDocument:
    """Parse a document file or URL into plain text.

    Supports:
    - Files: PDF, DOCX, PPTX, XLSX, MD, TXT, HTML (via Docling)
    - URLs: any http/https URL (via Jina Reader)
    """
    path_str = str(file_path)

    # Handle URLs
    if path_str.startswith("http://") or path_str.startswith("https://"):
        return parse_url(path_str)

    file_path = Path(file_path).resolve()
    suffix = file_path.suffix.lower().lstrip(".")

    # For plain text and markdown, read directly (faster than Docling)
    if suffix in ("md", "txt"):
        text = file_path.read_text(encoding="utf-8")
        return ParsedDocument(
            text=text,
            source_path=file_path,
            format=suffix,
            char_count=len(text),
        )

    # For rich formats, use Docling
    converter = _get_converter()
    result = converter.convert(str(file_path))
    text = result.document.export_to_markdown()

    return ParsedDocument(
        text=text,
        source_path=file_path,
        format=suffix,
        char_count=len(text),
    )
```

- [ ] **Step 9: Run parser tests**

```bash
pytest tests/test_ingestion.py -v
```
Expected: PASS

- [ ] **Step 10: Write failing tests for SQLite metadata storage**

```python
# openraven/tests/test_storage.py
from pathlib import Path

import pytest

from openraven.storage import MetadataStore, FileRecord


def test_store_and_retrieve_file_record(tmp_path: Path) -> None:
    store = MetadataStore(tmp_path / "test.db")
    record = FileRecord(
        path="/docs/report.pdf",
        hash="abc123",
        format="pdf",
        char_count=5000,
        status="ingested",
    )
    store.upsert_file(record)
    retrieved = store.get_file("/docs/report.pdf")
    assert retrieved is not None
    assert retrieved.hash == "abc123"
    assert retrieved.status == "ingested"


def test_upsert_updates_existing_record(tmp_path: Path) -> None:
    store = MetadataStore(tmp_path / "test.db")
    store.upsert_file(FileRecord(path="/a.md", hash="v1", format="md", char_count=100, status="ingested"))
    store.upsert_file(FileRecord(path="/a.md", hash="v2", format="md", char_count=200, status="extracted"))
    record = store.get_file("/a.md")
    assert record is not None
    assert record.hash == "v2"
    assert record.status == "extracted"


def test_get_nonexistent_file_returns_none(tmp_path: Path) -> None:
    store = MetadataStore(tmp_path / "test.db")
    assert store.get_file("/nope.txt") is None


def test_list_files(tmp_path: Path) -> None:
    store = MetadataStore(tmp_path / "test.db")
    store.upsert_file(FileRecord(path="/a.md", hash="h1", format="md", char_count=100, status="ingested"))
    store.upsert_file(FileRecord(path="/b.pdf", hash="h2", format="pdf", char_count=200, status="ingested"))
    files = store.list_files()
    assert len(files) == 2
```

- [ ] **Step 11: Run storage tests to verify they fail**

```bash
pytest tests/test_storage.py -v
```
Expected: FAIL

- [ ] **Step 12: Implement SQLite metadata store**

```python
# openraven/src/openraven/storage.py
from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path


@dataclass
class FileRecord:
    """Metadata record for an ingested file."""

    path: str
    hash: str
    format: str
    char_count: int
    status: str  # "ingested", "extracted", "graphed", "compiled"


class MetadataStore:
    """SQLite-backed metadata store for tracking file processing state."""

    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path
        self._conn = sqlite3.connect(str(db_path))
        self._conn.row_factory = sqlite3.Row
        self._create_tables()

    def _create_tables(self) -> None:
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS files (
                path TEXT PRIMARY KEY,
                hash TEXT NOT NULL,
                format TEXT NOT NULL,
                char_count INTEGER NOT NULL,
                status TEXT NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        self._conn.commit()

    def upsert_file(self, record: FileRecord) -> None:
        self._conn.execute(
            """
            INSERT INTO files (path, hash, format, char_count, status)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(path) DO UPDATE SET
                hash=excluded.hash,
                format=excluded.format,
                char_count=excluded.char_count,
                status=excluded.status,
                updated_at=CURRENT_TIMESTAMP
            """,
            (record.path, record.hash, record.format, record.char_count, record.status),
        )
        self._conn.commit()

    def get_file(self, path: str) -> FileRecord | None:
        row = self._conn.execute("SELECT * FROM files WHERE path = ?", (path,)).fetchone()
        if row is None:
            return None
        return FileRecord(
            path=row["path"],
            hash=row["hash"],
            format=row["format"],
            char_count=row["char_count"],
            status=row["status"],
        )

    def list_files(self, status: str | None = None) -> list[FileRecord]:
        if status:
            rows = self._conn.execute("SELECT * FROM files WHERE status = ?", (status,)).fetchall()
        else:
            rows = self._conn.execute("SELECT * FROM files").fetchall()
        return [
            FileRecord(path=r["path"], hash=r["hash"], format=r["format"],
                       char_count=r["char_count"], status=r["status"])
            for r in rows
        ]

    def close(self) -> None:
        self._conn.close()
```

- [ ] **Step 13: Run all tests**

```bash
pytest tests/test_ingestion.py tests/test_storage.py -v
```
Expected: All PASS

- [ ] **Step 14: Commit**

```bash
git add -A
git commit -m "feat: add document ingestion layer (Docling parser, file hasher, SQLite metadata store)"
```

---

## Task 3: LangExtract Entity Extraction Layer

**Files:**
- Create: `src/openraven/extraction/extractor.py`
- Create: `src/openraven/extraction/schemas/base.py`
- Create: `src/openraven/extraction/schemas/engineering.py`
- Create: `src/openraven/extraction/schemas/finance.py`
- Create: `tests/test_extraction.py`

- [ ] **Step 1: Write failing tests for extraction**

```python
# openraven/tests/test_extraction.py
from __future__ import annotations

import pytest

from openraven.extraction.extractor import (
    extract_entities,
    ExtractionResult,
    Entity,
)
from openraven.extraction.schemas.base import BASE_SCHEMA


def test_extraction_result_structure() -> None:
    """Test that ExtractionResult has the expected fields."""
    entity = Entity(
        name="Event-Driven Architecture",
        entity_type="concept",
        context="We chose event-driven architecture using Apache Kafka",
        source_document="test.md",
        char_start=100,
        char_end=150,
    )
    result = ExtractionResult(entities=[entity], source_document="test.md")
    assert len(result.entities) == 1
    assert result.entities[0].name == "Event-Driven Architecture"
    assert result.entities[0].char_start == 100


def test_enrich_text_with_entities() -> None:
    """Test that enriched text includes entity markers for LightRAG."""
    from openraven.extraction.extractor import enrich_text_for_rag

    entity = Entity(
        name="Kafka",
        entity_type="technology",
        context="using Apache Kafka for messaging",
        source_document="test.md",
        char_start=0,
        char_end=31,
    )
    result = ExtractionResult(entities=[entity], source_document="test.md")
    enriched = enrich_text_for_rag("using Apache Kafka for messaging", result)
    assert "Kafka" in enriched
    assert "[ENTITY:" in enriched or "<<" in enriched  # entity markers present
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_extraction.py -v
```
Expected: FAIL

- [ ] **Step 3: Implement data models and enrichment logic**

```python
# openraven/src/openraven/extraction/extractor.py
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field

import langextract as lx


@dataclass
class Entity:
    """A single extracted entity with source grounding."""

    name: str
    entity_type: str  # "concept", "decision", "method", "person", "technology", etc.
    context: str  # surrounding text from source
    source_document: str
    char_start: int | None = None
    char_end: int | None = None
    attributes: dict = field(default_factory=dict)


@dataclass
class ExtractionResult:
    """Result of entity extraction from a single document."""

    entities: list[Entity]
    source_document: str


def _run_langextract(text: str, schema: dict, model_id: str):
    """Synchronous wrapper for lx.extract (runs in thread to avoid blocking event loop)."""
    return lx.extract(
        text_or_documents=text,
        prompt_description=schema["prompt_description"],
        examples=schema.get("examples", []),
        model_id=model_id,
    )


async def extract_entities(
    text: str,
    source_document: str,
    schema: dict,
    model_id: str = "gemini-2.5-flash",
) -> ExtractionResult:
    """Extract entities from text using LangExtract with source grounding.

    Args:
        text: The document text to extract from.
        source_document: File path or identifier of the source.
        schema: Domain-specific extraction schema (prompt + examples).
        model_id: LLM model to use for extraction.

    Returns:
        ExtractionResult with grounded entities.
    """
    # lx.extract() is synchronous — run in thread to avoid blocking the event loop
    result = await asyncio.to_thread(_run_langextract, text, schema, model_id)

    entities = []
    for extraction in result.extractions:
        # LangExtract returns objects with attributes (not dicts).
        # char_interval is a tuple (start, end) or None if ungrounded.
        char_interval = getattr(extraction, "char_interval", None)
        extraction_text = getattr(extraction, "extraction_text", str(extraction))
        extraction_class = getattr(extraction, "extraction_class", "concept")
        attributes = getattr(extraction, "attributes", {})

        entities.append(Entity(
            name=extraction_text,
            entity_type=extraction_class,
            context=extraction_text,
            source_document=source_document,
            char_start=char_interval[0] if char_interval else None,
            char_end=char_interval[1] if char_interval else None,
            attributes=attributes if isinstance(attributes, dict) else {},
        ))

    return ExtractionResult(entities=entities, source_document=source_document)


def enrich_text_for_rag(text: str, extraction_result: ExtractionResult) -> str:
    """Enrich document text with entity markers for better LightRAG ingestion.

    Prepends an entity summary section before the original text so LightRAG
    can identify entities and relationships more accurately.
    """
    if not extraction_result.entities:
        return text

    entity_lines = []
    for e in extraction_result.entities:
        loc = ""
        if e.char_start is not None and e.char_end is not None:
            loc = f" [source:{e.source_document}:{e.char_start}-{e.char_end}]"
        entity_lines.append(
            f"[ENTITY:{e.entity_type}] {e.name}{loc}"
        )

    header = "=== Extracted Entities ===\n" + "\n".join(entity_lines) + "\n=== End Entities ===\n\n"
    return header + text
```

- [ ] **Step 4: Implement base extraction schema**

```python
# openraven/src/openraven/extraction/schemas/base.py
"""Base (generic) extraction schema for knowledge extraction."""

BASE_SCHEMA: dict = {
    "prompt_description": (
        "Extract key knowledge entities from this document. "
        "Identify: concepts, decisions, methods/frameworks, technologies, "
        "people, organizations, and specific claims or findings. "
        "For each entity, capture the type and the surrounding context."
    ),
    "examples": [],
}
```

- [ ] **Step 5: Implement engineering domain schema**

```python
# openraven/src/openraven/extraction/schemas/engineering.py
"""Engineering domain extraction schema for ADRs, tech specs, and architecture docs."""

ENGINEERING_SCHEMA: dict = {
    "prompt_description": (
        "Extract knowledge entities from this technical/engineering document. "
        "Focus on: architecture decisions (and their rationale), technology choices, "
        "trade-offs evaluated, performance metrics, system components, APIs, "
        "design patterns used, risks identified, and lessons learned. "
        "Capture WHY decisions were made, not just WHAT was decided."
    ),
    "examples": [],
}
```

- [ ] **Step 6: Implement finance domain schema**

```python
# openraven/src/openraven/extraction/schemas/finance.py
"""Finance domain extraction schema for research reports and earnings calls."""

FINANCE_SCHEMA: dict = {
    "prompt_description": (
        "Extract knowledge entities from this financial/investment document. "
        "Focus on: companies and tickers, financial metrics (P/E, revenue, margins), "
        "industry trends, analyst opinions and price targets, risk factors, "
        "competitive dynamics, regulatory impacts, and valuation methodologies. "
        "Capture specific numbers, dates, and sources of claims."
    ),
    "examples": [],
}
```

- [ ] **Step 7: Run tests**

```bash
pytest tests/test_extraction.py -v
```
Expected: PASS (data model + enrichment tests pass; integration test with real API is separate)

- [ ] **Step 8: Commit**

```bash
git add -A
git commit -m "feat: add LangExtract entity extraction layer with engineering and finance schemas"
```

---

## Task 4: LightRAG Knowledge Graph Layer

**Files:**
- Create: `src/openraven/graph/rag.py`
- Create: `tests/test_graph.py`

- [ ] **Step 1: Write failing tests**

```python
# openraven/tests/test_graph.py
from __future__ import annotations

import os
from pathlib import Path

import pytest

from openraven.graph.rag import RavenGraph


@pytest.fixture
def graph(tmp_working_dir: Path) -> RavenGraph:
    """Create a lazy-initialized RavenGraph for unit tests (no API calls)."""
    return RavenGraph.create_lazy(working_dir=tmp_working_dir / "lightrag_data")


def test_raven_graph_initializes(graph: RavenGraph) -> None:
    assert graph is not None
    assert graph.working_dir.exists()


@pytest.mark.skipif(
    not os.environ.get("GEMINI_API_KEY"),
    reason="GEMINI_API_KEY not set — skipping integration test",
)
async def test_insert_and_query(tmp_working_dir: Path) -> None:
    """Integration test: insert + query (requires GEMINI_API_KEY)."""
    graph = await RavenGraph.create(working_dir=tmp_working_dir / "lightrag_int")
    text = "Apache Kafka is a distributed event streaming platform used for real-time data pipelines."
    await graph.insert(text, source="test.md")
    assert any(graph.working_dir.iterdir())


def test_export_graphml(graph: RavenGraph, tmp_path: Path) -> None:
    """Test GraphML export produces a file."""
    output = tmp_path / "graph.graphml"
    graph.export_graphml(output)
    assert output.exists()
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_graph.py -v
```
Expected: FAIL

- [ ] **Step 3: Implement LightRAG wrapper**

```python
# openraven/src/openraven/graph/rag.py
from __future__ import annotations

from pathlib import Path
from typing import Literal

from lightrag import LightRAG, QueryParam

QueryMode = Literal["local", "global", "hybrid", "mix", "naive", "bypass"]


class RavenGraph:
    """Wrapper around LightRAG for knowledge graph operations.

    Uses NetworkX + NanoVectorDB for local storage (M1).
    Production backends (Neo4j + Qdrant) will be added in M2+.

    IMPORTANT: Use the async factory `RavenGraph.create()` instead of `__init__`
    to ensure LightRAG storage backends are initialized before use.
    """

    def __init__(self, working_dir: Path, rag: LightRAG) -> None:
        """Do not call directly — use RavenGraph.create() instead."""
        self.working_dir = Path(working_dir)
        self._rag = rag
        self._initialized = False

    @classmethod
    async def create(
        cls,
        working_dir: Path,
        llm_model: str = "gemini-2.5-flash",
        llm_api_key: str | None = None,
        embedding_model: str = "text-embedding-004",
    ) -> RavenGraph:
        """Async factory that creates and initializes RavenGraph.

        LightRAG requires `initialize_storages()` before any insert/query.
        This factory ensures that invariant is met.
        """
        working_dir = Path(working_dir)
        working_dir.mkdir(parents=True, exist_ok=True)

        llm_func = cls._make_llm_func(llm_model, llm_api_key)
        embed_func = cls._make_embedding_func(embedding_model, llm_api_key)

        rag = LightRAG(
            working_dir=str(working_dir),
            llm_model_func=llm_func,
            embedding_func=embed_func,
        )
        await rag.initialize_storages()

        instance = cls(working_dir, rag)
        instance._initialized = True
        return instance

    @classmethod
    def create_lazy(
        cls,
        working_dir: Path,
        llm_model: str = "gemini-2.5-flash",
        llm_api_key: str | None = None,
        embedding_model: str = "text-embedding-004",
    ) -> RavenGraph:
        """Synchronous constructor for contexts where async isn't available (tests, CLI).

        Defers initialization — must call `await graph.ensure_initialized()` before use.
        """
        working_dir = Path(working_dir)
        working_dir.mkdir(parents=True, exist_ok=True)

        llm_func = cls._make_llm_func(llm_model, llm_api_key)
        embed_func = cls._make_embedding_func(embedding_model, llm_api_key)

        rag = LightRAG(
            working_dir=str(working_dir),
            llm_model_func=llm_func,
            embedding_func=embed_func,
        )
        return cls(working_dir, rag)

    async def ensure_initialized(self) -> None:
        """Initialize storage backends if not already done."""
        if not self._initialized:
            await self._rag.initialize_storages()
            self._initialized = True

    @staticmethod
    def _make_llm_func(model: str, api_key: str | None):
        """Create the LLM function for LightRAG.

        LightRAG always uses Gemini (via OpenAI-compatible endpoint) for graph
        operations. Claude is used separately for wiki generation only (via
        the Anthropic SDK directly in wiki/compiler.py).
        """
        from lightrag.llm.openai import openai_complete_if_cache
        from functools import partial
        import os

        if "gemini" in model:
            key = api_key or os.environ.get("GEMINI_API_KEY", "")
            return partial(
                openai_complete_if_cache,
                model=model,
                api_key=key,
                base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
            )
        else:
            # Default: OpenAI-compatible (also works for other providers)
            key = api_key or os.environ.get("OPENAI_API_KEY", "")
            return partial(openai_complete_if_cache, model=model, api_key=key)

    @staticmethod
    def _make_embedding_func(model: str, api_key: str | None):
        """Create the embedding function for LightRAG.

        Default: Google text-embedding-004 (multilingual, supports zh-TW + English).
        For self-hosted: consider bge-m3 or multilingual-e5-large via Ollama.
        """
        from lightrag.llm.openai import openai_embed
        from functools import partial
        import os

        if "text-embedding" in model:
            # Google's text-embedding via OpenAI-compatible endpoint
            key = api_key or os.environ.get("GEMINI_API_KEY", "")
            return partial(
                openai_embed,
                model=model,
                api_key=key,
                base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
            )
        return partial(openai_embed, model=model)

    async def insert(self, text: str, source: str = "") -> None:
        """Insert text into the knowledge graph."""
        await self.ensure_initialized()
        await self._rag.ainsert(text)

    async def query(self, question: str, mode: QueryMode = "mix") -> str:
        """Query the knowledge graph."""
        await self.ensure_initialized()
        result = await self._rag.aquery(
            question,
            param=QueryParam(mode=mode),
        )
        return result

    def export_graphml(self, output_path: Path) -> None:
        """Export the knowledge graph as GraphML for visualization."""
        import networkx as nx

        output_path = Path(output_path)
        graph_file = self.working_dir / "graph_chunk_entity_relation.graphml"
        if graph_file.exists():
            G = nx.read_graphml(str(graph_file))
            nx.write_graphml(G, str(output_path))
        else:
            G = nx.Graph()
            nx.write_graphml(G, str(output_path))

    def get_stats(self) -> dict:
        """Return basic statistics about the knowledge graph."""
        import networkx as nx

        graph_file = self.working_dir / "graph_chunk_entity_relation.graphml"
        if not graph_file.exists():
            return {"nodes": 0, "edges": 0, "topics": []}

        G = nx.read_graphml(str(graph_file))
        return {
            "nodes": G.number_of_nodes(),
            "edges": G.number_of_edges(),
            "topics": list(G.nodes())[:20],
        }
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/test_graph.py -v
```
Expected: PASS for structure tests; async integration test may need API keys

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "feat: add LightRAG knowledge graph layer with query modes and GraphML export"
```

---

## Task 5: Wiki Article Generation (Stage 3)

**Files:**
- Create: `src/openraven/wiki/compiler.py`
- Create: `tests/test_wiki.py`

- [ ] **Step 1: Write failing tests**

```python
# openraven/tests/test_wiki.py
from __future__ import annotations

from pathlib import Path

import pytest

from openraven.wiki.compiler import WikiArticle, compile_article, render_article_markdown


def test_wiki_article_structure() -> None:
    article = WikiArticle(
        title="Event-Driven Architecture",
        summary="A software design pattern using events for communication.",
        sections=[
            {"heading": "Overview", "content": "Events decouple producers from consumers."},
            {"heading": "Trade-offs", "content": "Added complexity but better scalability."},
        ],
        sources=[
            {"document": "adr-001.md", "excerpt": "We chose event-driven...", "char_start": 100, "char_end": 140},
        ],
        related_topics=["Apache Kafka", "CQRS", "Microservices"],
        confidence_score=0.85,
    )
    assert article.title == "Event-Driven Architecture"
    assert len(article.sections) == 2
    assert len(article.sources) == 1
    assert article.confidence_score == 0.85


def test_render_article_markdown() -> None:
    article = WikiArticle(
        title="Kafka",
        summary="Distributed streaming platform.",
        sections=[{"heading": "Usage", "content": "Used for real-time pipelines."}],
        sources=[{"document": "notes.md", "excerpt": "Kafka is used...", "char_start": 0, "char_end": 20}],
        related_topics=["Event Streaming"],
        confidence_score=0.9,
    )
    md = render_article_markdown(article)
    assert "# Kafka" in md
    assert "Distributed streaming platform" in md
    assert "Usage" in md
    assert "notes.md" in md
    assert "Related" in md
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_wiki.py -v
```
Expected: FAIL

- [ ] **Step 3: Implement wiki compiler**

```python
# openraven/src/openraven/wiki/compiler.py
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import anthropic


@dataclass
class WikiArticle:
    """A compiled wiki article about a knowledge topic."""

    title: str
    summary: str
    sections: list[dict]  # [{"heading": str, "content": str}]
    sources: list[dict]  # [{"document": str, "excerpt": str, "char_start": int, "char_end": int}]
    related_topics: list[str]
    confidence_score: float  # 0.0 - 1.0


COMPILE_PROMPT = """\
You are a knowledge compiler. Given a topic and retrieved context from a personal knowledge graph,
write a structured wiki article.

Rules:
1. Every factual claim MUST cite a source using [Source: document_name] format
2. If information is inferred rather than directly stated, mark it as [Inferred]
3. Include a confidence score (0.0-1.0) based on how well-sourced the article is
4. Write in the same language as the majority of the source material
5. Be concise but thorough

Topic: {topic}

Retrieved Context:
{context}

Source Documents:
{sources}

Respond in this exact JSON format:
{{
  "summary": "2-3 sentence summary",
  "sections": [
    {{"heading": "section name", "content": "section content with [Source: doc] citations"}}
  ],
  "related_topics": ["topic1", "topic2"],
  "confidence_score": 0.85
}}
"""


async def compile_article(
    topic: str,
    context: str,
    sources: list[dict],
    api_key: str,
    model: str = "claude-sonnet-4-6",
) -> WikiArticle:
    """Compile a wiki article for a topic using retrieved RAG context.

    Args:
        topic: The entity/concept name to write about.
        context: Retrieved context from LightRAG query.
        sources: List of source document references with positions.
        api_key: Anthropic API key.
        model: Claude model to use for generation.
    """
    import json

    source_text = "\n".join(
        f"- {s['document']} (chars {s.get('char_start', '?')}-{s.get('char_end', '?')}): {s.get('excerpt', '')}"
        for s in sources
    )

    prompt = COMPILE_PROMPT.format(
        topic=topic,
        context=context,
        sources=source_text,
    )

    client = anthropic.AsyncAnthropic(api_key=api_key)
    response = await client.messages.create(
        model=model,
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}],
    )

    content = response.content[0].text
    # Parse JSON from response (handle markdown code blocks)
    if "```json" in content:
        content = content.split("```json")[1].split("```")[0]
    elif "```" in content:
        content = content.split("```")[1].split("```")[0]

    data = json.loads(content.strip())

    return WikiArticle(
        title=topic,
        summary=data["summary"],
        sections=data["sections"],
        sources=sources,
        related_topics=data.get("related_topics", []),
        confidence_score=data.get("confidence_score", 0.5),
    )


def render_article_markdown(article: WikiArticle) -> str:
    """Render a WikiArticle as a Markdown string."""
    lines = [
        f"# {article.title}",
        "",
        f"**Confidence:** {article.confidence_score:.0%}",
        "",
        article.summary,
        "",
    ]

    for section in article.sections:
        lines.append(f"## {section['heading']}")
        lines.append("")
        lines.append(section["content"])
        lines.append("")

    if article.related_topics:
        lines.append("## Related Topics")
        lines.append("")
        for topic in article.related_topics:
            lines.append(f"- [[{topic}]]")
        lines.append("")

    if article.sources:
        lines.append("## Sources")
        lines.append("")
        for src in article.sources:
            excerpt = src.get("excerpt", "")[:80]
            lines.append(f"- **{src['document']}** (chars {src.get('char_start', '?')}-{src.get('char_end', '?')}): _{excerpt}_")
        lines.append("")

    return "\n".join(lines)


async def compile_wiki_for_graph(
    graph,
    entities: list[str],
    sources_map: dict,
    api_key: str,
    output_dir: Path,
    model: str = "claude-sonnet-4-6",
    max_concurrent: int = 5,
    on_progress: callable | None = None,
) -> list[WikiArticle]:
    """Compile wiki articles for a list of entities from the knowledge graph.

    Uses asyncio.Semaphore for bounded concurrency (default 5 parallel).

    Args:
        graph: RavenGraph instance.
        entities: List of entity names to compile articles for.
        sources_map: Mapping of entity name -> list of source dicts.
        api_key: Anthropic API key.
        output_dir: Directory to save generated markdown files.
        model: Claude model for generation.
        max_concurrent: Max parallel wiki compilations.
        on_progress: Optional callback(completed: int, total: int) for progress.
    """
    import asyncio
    import logging

    logger = logging.getLogger(__name__)

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    semaphore = asyncio.Semaphore(max_concurrent)
    completed_count = 0

    async def compile_one(entity_name: str) -> WikiArticle | None:
        nonlocal completed_count
        async with semaphore:
            try:
                context = await graph.query(
                    f"Tell me everything about: {entity_name}",
                    mode="local",
                )
                sources = sources_map.get(entity_name, [])

                article = await compile_article(
                    topic=entity_name,
                    context=context,
                    sources=sources,
                    api_key=api_key,
                    model=model,
                )

                safe_name = entity_name.replace("/", "_").replace(" ", "_").lower()
                md_path = output_dir / f"{safe_name}.md"
                md_path.write_text(render_article_markdown(article), encoding="utf-8")

                completed_count += 1
                if on_progress:
                    on_progress(completed_count, len(entities))

                return article
            except Exception as e:
                logger.warning(f"Failed to compile wiki for '{entity_name}': {e}")
                completed_count += 1
                return None

    results = await asyncio.gather(*[compile_one(name) for name in entities])
    return [a for a in results if a is not None]
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/test_wiki.py -v
```
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "feat: add wiki article compiler with source citations and confidence scoring"
```

---

## Task 6: Proactive Discovery & Health Reporter

**Files:**
- Create: `src/openraven/discovery/analyzer.py`
- Create: `src/openraven/health/reporter.py`
- Create: `tests/test_discovery.py`
- Create: `tests/test_health.py`

- [ ] **Step 1: Write failing tests for discovery**

```python
# openraven/tests/test_discovery.py
from __future__ import annotations

from openraven.discovery.analyzer import (
    DiscoveryInsight,
    analyze_themes,
)


def test_discovery_insight_structure() -> None:
    insight = DiscoveryInsight(
        insight_type="theme",
        title="Event-Driven Architecture",
        description="Found 5 documents discussing event-driven patterns",
        related_entities=["Kafka", "RabbitMQ", "CQRS"],
        document_count=5,
    )
    assert insight.insight_type == "theme"
    assert len(insight.related_entities) == 3


def test_analyze_themes_from_graph_stats() -> None:
    """Test theme analysis from basic graph statistics."""
    graph_stats = {
        "nodes": 45,
        "edges": 120,
        "topics": [
            "Event-Driven Architecture", "Apache Kafka", "Microservices",
            "CQRS", "Database Sharding", "PostgreSQL", "Redis",
            "REST API", "GraphQL", "gRPC",
        ],
    }
    insights = analyze_themes(graph_stats)
    assert len(insights) > 0
    assert all(isinstance(i, DiscoveryInsight) for i in insights)
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_discovery.py -v
```
Expected: FAIL

- [ ] **Step 3: Implement discovery analyzer**

```python
# openraven/src/openraven/discovery/analyzer.py
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class DiscoveryInsight:
    """A proactive insight discovered from the knowledge graph."""

    insight_type: str  # "theme", "cluster", "gap", "trend"
    title: str
    description: str
    related_entities: list[str] = field(default_factory=list)
    document_count: int = 0


def analyze_themes(graph_stats: dict) -> list[DiscoveryInsight]:
    """Analyze knowledge graph statistics to discover themes.

    This is the "first surprise moment" — show users what patterns
    exist in their knowledge base after initial ingestion.
    """
    insights = []
    topics = graph_stats.get("topics", [])
    node_count = graph_stats.get("nodes", 0)
    edge_count = graph_stats.get("edges", 0)

    if node_count > 0:
        insights.append(DiscoveryInsight(
            insight_type="theme",
            title="Knowledge Base Overview",
            description=(
                f"Your knowledge base contains {node_count} concepts "
                f"with {edge_count} connections between them."
            ),
            related_entities=topics[:10],
            document_count=node_count,
        ))

    # Group topics by simple keyword clustering
    if len(topics) >= 3:
        insights.append(DiscoveryInsight(
            insight_type="cluster",
            title=f"Top Knowledge Areas",
            description=f"Found {len(topics)} distinct topics in your knowledge base.",
            related_entities=topics[:10],
            document_count=len(topics),
        ))

    return insights


async def discover_insights_with_llm(
    graph,
    api_key: str,
    model: str = "claude-sonnet-4-6",
) -> list[DiscoveryInsight]:
    """Use LLM + knowledge graph to generate deeper proactive insights.

    Queries the graph in global mode to find cross-document patterns,
    recurring frameworks, and knowledge gaps.
    """
    import json
    import anthropic

    # First, get global overview from LightRAG
    overview = await graph.query(
        "What are the main themes, recurring patterns, and frameworks in this knowledge base? "
        "Identify clusters of related topics and any notable connections between different areas.",
        mode="global",
    )

    # Then ask LLM to structure the insights
    client = anthropic.AsyncAnthropic(api_key=api_key)
    response = await client.messages.create(
        model=model,
        max_tokens=1500,
        messages=[{"role": "user", "content": f"""Based on this knowledge base overview, generate 3-5 proactive discovery insights.

Overview:
{overview}

Return JSON array:
[
  {{
    "insight_type": "theme|cluster|gap|trend",
    "title": "short title",
    "description": "1-2 sentence description of what was found",
    "related_entities": ["entity1", "entity2"]
  }}
]
"""}],
    )

    content = response.content[0].text
    if "```json" in content:
        content = content.split("```json")[1].split("```")[0]
    elif "```" in content:
        content = content.split("```")[1].split("```")[0]

    raw_insights = json.loads(content.strip())

    return [
        DiscoveryInsight(
            insight_type=item["insight_type"],
            title=item["title"],
            description=item["description"],
            related_entities=item.get("related_entities", []),
        )
        for item in raw_insights
    ]
```

- [ ] **Step 4: Write failing tests for health reporter**

```python
# openraven/tests/test_health.py
from __future__ import annotations

from openraven.health.reporter import HealthReport, generate_health_report


def test_health_report_structure() -> None:
    report = HealthReport(
        total_files=10,
        total_entities=127,
        total_connections=340,
        topic_count=8,
        top_topics=["Architecture", "Testing", "Deployment"],
        languages_detected=["en", "zh-TW"],
        confidence_avg=0.82,
    )
    assert report.total_files == 10
    assert report.topic_count == 8


def test_generate_health_report_from_stats() -> None:
    file_records = [
        {"path": "/a.md", "status": "compiled", "char_count": 1000},
        {"path": "/b.pdf", "status": "compiled", "char_count": 5000},
    ]
    graph_stats = {"nodes": 45, "edges": 120, "topics": ["A", "B", "C"]}

    report = generate_health_report(file_records, graph_stats)
    assert report.total_files == 2
    assert report.total_entities == 45
    assert report.total_connections == 120
    assert report.topic_count == 3
```

- [ ] **Step 5: Run tests to verify they fail**

```bash
pytest tests/test_health.py -v
```
Expected: FAIL

- [ ] **Step 6: Implement health reporter**

```python
# openraven/src/openraven/health/reporter.py
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class HealthReport:
    """Knowledge base health report."""

    total_files: int
    total_entities: int
    total_connections: int
    topic_count: int
    top_topics: list[str] = field(default_factory=list)
    languages_detected: list[str] = field(default_factory=list)
    confidence_avg: float = 0.0


def generate_health_report(
    file_records: list[dict],
    graph_stats: dict,
    wiki_articles: list | None = None,
) -> HealthReport:
    """Generate a health report from current knowledge base state."""
    total_files = len(file_records)
    total_entities = graph_stats.get("nodes", 0)
    total_connections = graph_stats.get("edges", 0)
    topics = graph_stats.get("topics", [])

    confidence_avg = 0.0
    if wiki_articles:
        scores = [a.confidence_score for a in wiki_articles if hasattr(a, "confidence_score")]
        if scores:
            confidence_avg = sum(scores) / len(scores)

    return HealthReport(
        total_files=total_files,
        total_entities=total_entities,
        total_connections=total_connections,
        topic_count=len(topics),
        top_topics=topics[:10],
        confidence_avg=confidence_avg,
    )


def format_health_report(report: HealthReport) -> str:
    """Format a health report as a human-readable string."""
    lines = [
        "=== Knowledge Base Health Report ===",
        "",
        f"Files processed:    {report.total_files}",
        f"Concepts extracted: {report.total_entities}",
        f"Connections found:  {report.total_connections}",
        f"Topic areas:        {report.topic_count}",
        "",
    ]

    if report.top_topics:
        lines.append("Top topics:")
        for topic in report.top_topics[:10]:
            lines.append(f"  - {topic}")
        lines.append("")

    if report.confidence_avg > 0:
        lines.append(f"Average confidence: {report.confidence_avg:.0%}")
        lines.append("")

    lines.append("====================================")
    return "\n".join(lines)
```

- [ ] **Step 7: Run all tests**

```bash
pytest tests/test_discovery.py tests/test_health.py -v
```
Expected: PASS

- [ ] **Step 8: Commit**

```bash
git add -A
git commit -m "feat: add proactive discovery analyzer and knowledge base health reporter"
```

---

## Task 7: Pipeline Orchestrator

**Files:**
- Create: `src/openraven/pipeline.py`
- Create: `tests/test_pipeline.py`

- [ ] **Step 1: Write failing tests**

```python
# openraven/tests/test_pipeline.py
from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from openraven.config import RavenConfig
from openraven.pipeline import RavenPipeline, PipelineResult


def test_pipeline_initializes(config: RavenConfig) -> None:
    pipeline = RavenPipeline(config)
    assert pipeline.config == config


def test_pipeline_result_structure() -> None:
    result = PipelineResult(
        files_processed=5,
        entities_extracted=42,
        articles_generated=8,
        errors=[],
    )
    assert result.files_processed == 5
    assert result.has_errors is False


def test_pipeline_result_with_errors() -> None:
    result = PipelineResult(
        files_processed=5,
        entities_extracted=42,
        articles_generated=8,
        errors=["Failed to parse file.xlsx"],
    )
    assert result.has_errors is True
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_pipeline.py -v
```
Expected: FAIL

- [ ] **Step 3: Implement pipeline orchestrator**

```python
# openraven/src/openraven/pipeline.py
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

from openraven.config import RavenConfig
from openraven.extraction.extractor import Entity, ExtractionResult, extract_entities, enrich_text_for_rag
from openraven.extraction.schemas.base import BASE_SCHEMA
from openraven.graph.rag import RavenGraph
from openraven.health.reporter import HealthReport, generate_health_report, format_health_report
from openraven.ingestion.hasher import compute_file_hash
from openraven.ingestion.parser import ParsedDocument, parse_document
from openraven.storage import FileRecord, MetadataStore
from openraven.wiki.compiler import compile_wiki_for_graph

logger = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS = {".md", ".txt", ".pdf", ".docx", ".pptx", ".xlsx", ".html"}


@dataclass
class PipelineResult:
    """Result of a pipeline run."""

    files_processed: int
    entities_extracted: int
    articles_generated: int
    errors: list[str] = field(default_factory=list)

    @property
    def has_errors(self) -> bool:
        return len(self.errors) > 0


def _detect_schema(file_path: Path, text: str = "") -> dict:
    """Select extraction schema based on filename and content heuristics.

    Checks filename keywords first, then falls back to content keywords
    (first 2000 chars) for better detection of generic-named files.
    """
    name = file_path.name.lower()

    # Filename-based detection
    eng_keywords = ("adr", "architecture", "spec", "technical", "design", "system", "api", "infra")
    fin_keywords = ("research", "earnings", "financial", "valuation", "report", "investment", "analysis")

    if any(kw in name for kw in eng_keywords):
        from openraven.extraction.schemas.engineering import ENGINEERING_SCHEMA
        return ENGINEERING_SCHEMA
    elif any(kw in name for kw in fin_keywords):
        from openraven.extraction.schemas.finance import FINANCE_SCHEMA
        return FINANCE_SCHEMA

    # Content-based fallback (check first 2000 chars)
    sample = text[:2000].lower() if text else ""
    eng_content = ("architecture", "microservice", "api endpoint", "database", "deploy", "kubernetes", "docker")
    fin_content = ("revenue", "p/e", "earnings", "valuation", "market cap", "股價", "營收", "本益比", "殖利率")

    if any(kw in sample for kw in fin_content):
        from openraven.extraction.schemas.finance import FINANCE_SCHEMA
        return FINANCE_SCHEMA
    elif any(kw in sample for kw in eng_content):
        from openraven.extraction.schemas.engineering import ENGINEERING_SCHEMA
        return ENGINEERING_SCHEMA

    return BASE_SCHEMA


class RavenPipeline:
    """Orchestrates the 4-stage knowledge compilation pipeline.

    Stage 1: Document ingestion (Docling) — parse files to text
    Stage 2: Entity extraction (LangExtract) — extract entities with source grounding
    Stage 3: Knowledge graph (LightRAG) — build entity-relationship graph
    Stage 4: Wiki compilation (Claude) — generate structured articles
    """

    def __init__(self, config: RavenConfig) -> None:
        self.config = config
        self.store = MetadataStore(config.db_path)
        # Use lazy init — actual LightRAG storage init happens on first use
        self.graph = RavenGraph.create_lazy(
            working_dir=config.lightrag_dir,
            llm_model=config.llm_model,
            llm_api_key=config.gemini_api_key,
        )

    async def add_files(self, paths: list[Path]) -> PipelineResult:
        """Run the full 4-stage pipeline on a list of file paths.

        Supports both individual files and directories (recursive scan).
        Implements incremental updates — skips unchanged files.
        """
        errors: list[str] = []
        all_entities: list[Entity] = []
        sources_map: dict[str, list[dict]] = {}

        # Expand directories to individual files
        file_paths = self._expand_paths(paths)
        files_to_process = self._filter_unchanged(file_paths)

        if not files_to_process:
            logger.info("No new or changed files to process.")
            return PipelineResult(0, 0, 0)

        # --- Stage 1: Ingestion ---
        parsed_docs: list[ParsedDocument] = []
        for fp in files_to_process:
            try:
                doc = parse_document(fp)
                parsed_docs.append(doc)
                self.store.upsert_file(FileRecord(
                    path=str(fp), hash=compute_file_hash(fp),
                    format=doc.format, char_count=doc.char_count, status="ingested",
                ))
            except Exception as e:
                errors.append(f"Ingestion failed for {fp}: {e}")
                logger.error(f"Ingestion failed for {fp}", exc_info=True)

        # --- Stage 2: Extraction ---
        for doc in parsed_docs:
            try:
                schema = _detect_schema(doc.source_path, text=doc.text)
                result = await extract_entities(
                    text=doc.text,
                    source_document=str(doc.source_path),
                    schema=schema,
                    model_id=self.config.llm_model,
                )
                all_entities.extend(result.entities)

                # Build sources map for wiki compilation
                for entity in result.entities:
                    sources_map.setdefault(entity.name, []).append({
                        "document": str(doc.source_path),
                        "excerpt": entity.context[:100],
                        "char_start": entity.char_start,
                        "char_end": entity.char_end,
                    })

                # Enrich text and insert into LightRAG
                enriched = enrich_text_for_rag(doc.text, result)
                await self.graph.insert(enriched, source=str(doc.source_path))

                self.store.upsert_file(FileRecord(
                    path=str(doc.source_path), hash=compute_file_hash(doc.source_path),
                    format=doc.format, char_count=doc.char_count, status="graphed",
                ))
            except Exception as e:
                errors.append(f"Extraction/graph failed for {doc.source_path}: {e}")
                logger.error(f"Extraction failed for {doc.source_path}", exc_info=True)

        # --- Stage 3 & 4: Wiki Compilation ---
        entity_names = list({e.name for e in all_entities})[:50]  # Cap at 50 for M1
        articles = []
        if entity_names:
            try:
                articles = await compile_wiki_for_graph(
                    graph=self.graph,
                    entities=entity_names,
                    sources_map=sources_map,
                    api_key=self.config.anthropic_api_key,
                    output_dir=self.config.wiki_dir,
                    model=self.config.wiki_llm_model,
                )
            except Exception as e:
                errors.append(f"Wiki compilation failed: {e}")
                logger.error("Wiki compilation failed", exc_info=True)

        return PipelineResult(
            files_processed=len(parsed_docs),
            entities_extracted=len(all_entities),
            articles_generated=len(articles),
            errors=errors,
        )

    async def ask(self, question: str, mode: str = "mix") -> str:
        """Query the knowledge graph."""
        return await self.graph.query(question, mode=mode)

    def get_health_report(self) -> HealthReport:
        """Generate a health report for the knowledge base."""
        file_records = [
            {"path": r.path, "status": r.status, "char_count": r.char_count}
            for r in self.store.list_files()
        ]
        graph_stats = self.graph.get_stats()
        return generate_health_report(file_records, graph_stats)

    def _expand_paths(self, paths: list[Path]) -> list[Path | str]:
        """Expand directories to individual supported files. URLs pass through as strings."""
        result: list[Path | str] = []
        for p in paths:
            p_str = str(p)
            # URLs pass through directly
            if p_str.startswith("http://") or p_str.startswith("https://"):
                result.append(p_str)
                continue
            p = Path(p).resolve()
            if p.is_dir():
                for f in p.rglob("*"):
                    if f.is_file() and f.suffix.lower() in SUPPORTED_EXTENSIONS:
                        result.append(f)
            elif p.is_file() and p.suffix.lower() in SUPPORTED_EXTENSIONS:
                result.append(p)
        return result

    def _filter_unchanged(self, file_paths: list[Path | str]) -> list[Path | str]:
        """Filter out files that haven't changed since last processing. URLs always pass through."""
        changed: list[Path | str] = []
        for fp in file_paths:
            fp_str = str(fp)
            # URLs always re-process (can't hash remote content cheaply)
            if fp_str.startswith("http://") or fp_str.startswith("https://"):
                changed.append(fp)
                continue
            current_hash = compute_file_hash(Path(fp))
            existing = self.store.get_file(fp_str)
            if existing is None or existing.hash != current_hash:
                changed.append(fp)
        return changed
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/test_pipeline.py -v
```
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "feat: add 4-stage pipeline orchestrator with incremental updates"
```

---

## Task 8: CLI Tool (`raven` command)

**Files:**
- Create: `cli/main.py`
- Test: manual CLI testing

- [ ] **Step 1: Implement CLI with Click**

```python
# openraven/cli/main.py
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import click

from openraven.config import RavenConfig
from openraven.health.reporter import format_health_report


def _run_async(coro):
    """Run an async coroutine from sync Click commands."""
    return asyncio.run(coro)


def _resolve_working_dir(working_dir: str) -> str:
    """Resolve working dir: use explicit arg, or fall back to global default from `raven init`."""
    if working_dir != "~/my-knowledge":
        return working_dir
    global_config = Path("~/.openraven/default").expanduser()
    if global_config.exists():
        return global_config.read_text(encoding="utf-8").strip()
    return working_dir


@click.group()
@click.version_option(version="0.1.0", prog_name="raven")
def cli():
    """OpenRaven — AI-powered personal knowledge asset platform."""
    pass


@cli.command()
@click.argument("path", type=click.Path(), default="~/my-knowledge")
def init(path: str):
    """Initialize a new knowledge base."""
    import json

    config = RavenConfig(working_dir=path)

    # Persist config so subsequent commands don't need --working-dir
    config_file = config.working_dir / "raven.json"
    if not config_file.exists():
        config_file.write_text(json.dumps({
            "working_dir": str(config.working_dir),
            "llm_model": config.llm_model,
            "wiki_llm_model": config.wiki_llm_model,
            "embedding_model": config.embedding_model,
        }, indent=2, ensure_ascii=False), encoding="utf-8")

    # Also save a global pointer so `raven add` works without --working-dir
    global_config = Path("~/.openraven/default").expanduser()
    global_config.parent.mkdir(parents=True, exist_ok=True)
    global_config.write_text(str(config.working_dir), encoding="utf-8")

    click.echo(f"Initialized knowledge base at: {config.working_dir}")
    click.echo(f"Database: {config.db_path}")
    click.echo("")

    # Validate API keys
    if not config.gemini_api_key:
        click.echo("WARNING: GEMINI_API_KEY not set. Set it in your environment or .env file.")
        click.echo("  export GEMINI_API_KEY=your-key-here")
    if not config.anthropic_api_key:
        click.echo("WARNING: ANTHROPIC_API_KEY not set (needed for wiki generation).")
        click.echo("  export ANTHROPIC_API_KEY=your-key-here")

    click.echo("")
    click.echo("Next steps:")
    click.echo("  raven add ./docs/          # Add documents")
    click.echo('  raven ask "your question"   # Query your knowledge')


@cli.command()
@click.argument("paths", nargs=-1, type=click.Path(exists=True), required=True)
@click.option("--working-dir", "-w", default="~/my-knowledge", help="Knowledge base directory")
@click.option("--model", "-m", default="gemini-2.5-flash", help="LLM model for extraction")
def add(paths: tuple[str, ...], working_dir: str, model: str):
    """Add documents to the knowledge base."""
    from openraven.pipeline import RavenPipeline

    config = RavenConfig(working_dir=_resolve_working_dir(working_dir), llm_model=model)
    pipeline = RavenPipeline(config)

    file_paths = [Path(p) for p in paths]

    click.echo(f"Processing {len(file_paths)} path(s)...")
    click.echo("")

    result = _run_async(pipeline.add_files(file_paths))

    click.echo(f"Files processed:    {result.files_processed}")
    click.echo(f"Entities extracted: {result.entities_extracted}")
    click.echo(f"Articles generated: {result.articles_generated}")

    if result.has_errors:
        click.echo("")
        click.echo("Errors:")
        for err in result.errors:
            click.echo(f"  - {err}")
        sys.exit(1)


@cli.command()
@click.argument("question")
@click.option("--working-dir", "-w", default="~/my-knowledge", help="Knowledge base directory")
@click.option("--mode", "-m", default="mix", type=click.Choice(["local", "global", "mix", "hybrid", "naive"]))
def ask(question: str, working_dir: str, mode: str):
    """Ask a question to your knowledge base."""
    from openraven.pipeline import RavenPipeline

    config = RavenConfig(working_dir=working_dir)
    pipeline = RavenPipeline(config)

    answer = _run_async(pipeline.ask(question, mode=mode))
    click.echo(answer)


@cli.command()
@click.option("--working-dir", "-w", default="~/my-knowledge", help="Knowledge base directory")
def status(working_dir: str):
    """Show knowledge base health report."""
    from openraven.pipeline import RavenPipeline

    config = RavenConfig(working_dir=working_dir)
    pipeline = RavenPipeline(config)

    report = pipeline.get_health_report()
    click.echo(format_health_report(report))


@cli.command()
@click.option("--working-dir", "-w", default="~/my-knowledge", help="Knowledge base directory")
@click.option("--output", "-o", default="./knowledge_graph.graphml", help="Output GraphML file")
def graph(working_dir: str, output: str):
    """Export knowledge graph as GraphML."""
    from openraven.graph.rag import RavenGraph

    config = RavenConfig(working_dir=working_dir)
    raven_graph = RavenGraph(working_dir=config.lightrag_dir)

    output_path = Path(output).resolve()
    raven_graph.export_graphml(output_path)
    click.echo(f"Knowledge graph exported to: {output_path}")


@cli.command(name="export")
@click.option("--working-dir", "-w", default="~/my-knowledge", help="Knowledge base directory")
@click.option("--format", "-f", "fmt", default="markdown", type=click.Choice(["markdown", "json"]))
@click.option("--output", "-o", default="./export/", help="Output directory")
def export_cmd(working_dir: str, fmt: str, output: str):
    """Export knowledge base (wiki articles + graph)."""
    import shutil
    import json

    config = RavenConfig(working_dir=working_dir)
    output_dir = Path(output).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    wiki_dir = config.wiki_dir
    if wiki_dir.exists():
        if fmt == "markdown":
            for md_file in wiki_dir.glob("*.md"):
                shutil.copy2(md_file, output_dir / md_file.name)
            click.echo(f"Exported wiki articles to: {output_dir}")
        elif fmt == "json":
            articles = []
            for md_file in wiki_dir.glob("*.md"):
                articles.append({
                    "title": md_file.stem,
                    "content": md_file.read_text(encoding="utf-8"),
                })
            json_path = output_dir / "knowledge_base.json"
            json_path.write_text(json.dumps(articles, ensure_ascii=False, indent=2), encoding="utf-8")
            click.echo(f"Exported to: {json_path}")
    else:
        click.echo("No wiki articles found. Run 'raven add' first.")


if __name__ == "__main__":
    cli()
```

- [ ] **Step 2: Test CLI locally**

```bash
cd openraven
pip install -e ".[dev]"
raven --version
raven --help
raven init /tmp/test-kb
```
Expected: Version prints, help shows all commands, init creates directory

- [ ] **Step 3: Commit**

```bash
git add -A
git commit -m "feat: add raven CLI tool (init, add, ask, status, graph, export)"
```

---

## Task 9: FastAPI Server (Python API for TypeScript Backend)

**Files:**
- Create: `src/openraven/api/server.py`
- Create: `tests/test_api.py`

- [ ] **Step 1: Write failing tests for API endpoints**

```python
# openraven/tests/test_api.py
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from openraven.api.server import create_app
from openraven.config import RavenConfig


@pytest.fixture
def client(config: RavenConfig) -> TestClient:
    app = create_app(config)
    return TestClient(app)


def test_health_endpoint(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_status_endpoint(client: TestClient) -> None:
    response = client.get("/api/status")
    assert response.status_code == 200
    data = response.json()
    assert "total_files" in data
    assert "total_entities" in data


def test_ask_endpoint_requires_question(client: TestClient) -> None:
    response = client.post("/api/ask", json={})
    assert response.status_code == 422  # Validation error
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_api.py -v
```
Expected: FAIL

- [ ] **Step 3: Implement FastAPI server**

```python
# openraven/src/openraven/api/server.py
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from openraven.config import RavenConfig
from openraven.pipeline import RavenPipeline


class AskRequest(BaseModel):
    question: str
    mode: str = "mix"


class AskResponse(BaseModel):
    answer: str
    mode: str


class StatusResponse(BaseModel):
    total_files: int
    total_entities: int
    total_connections: int
    topic_count: int
    top_topics: list[str]
    confidence_avg: float


class IngestResponse(BaseModel):
    files_processed: int
    entities_extracted: int
    articles_generated: int
    errors: list[str]


class DiscoveryInsightResponse(BaseModel):
    insight_type: str
    title: str
    description: str
    related_entities: list[str]


def create_app(config: RavenConfig | None = None) -> FastAPI:
    """Create the FastAPI application."""
    if config is None:
        config = RavenConfig(working_dir="~/my-knowledge")

    app = FastAPI(
        title="OpenRaven API",
        version="0.1.0",
        description="OpenRaven knowledge engine API",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://localhost:3000"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    pipeline = RavenPipeline(config)

    @app.get("/health")
    async def health():
        return {"status": "ok", "version": "0.1.0"}

    @app.get("/api/status", response_model=StatusResponse)
    async def status():
        report = pipeline.get_health_report()
        return StatusResponse(
            total_files=report.total_files,
            total_entities=report.total_entities,
            total_connections=report.total_connections,
            topic_count=report.topic_count,
            top_topics=report.top_topics,
            confidence_avg=report.confidence_avg,
        )

    @app.post("/api/ask", response_model=AskResponse)
    async def ask(req: AskRequest):
        answer = await pipeline.ask(req.question, mode=req.mode)
        return AskResponse(answer=answer, mode=req.mode)

    @app.post("/api/ingest", response_model=IngestResponse)
    async def ingest(files: list[UploadFile] = File(...)):
        # Save uploaded files to ingestion directory
        saved_paths: list[Path] = []
        config.ingestion_dir.mkdir(parents=True, exist_ok=True)

        for upload in files:
            dest = config.ingestion_dir / upload.filename
            content = await upload.read()
            dest.write_bytes(content)
            saved_paths.append(dest)

        result = await pipeline.add_files(saved_paths)
        return IngestResponse(
            files_processed=result.files_processed,
            entities_extracted=result.entities_extracted,
            articles_generated=result.articles_generated,
            errors=result.errors,
        )

    @app.get("/api/discovery", response_model=list[DiscoveryInsightResponse])
    async def discovery():
        from openraven.discovery.analyzer import analyze_themes
        graph_stats = pipeline.graph.get_stats()
        insights = analyze_themes(graph_stats)
        return [
            DiscoveryInsightResponse(
                insight_type=i.insight_type,
                title=i.title,
                description=i.description,
                related_entities=i.related_entities,
            )
            for i in insights
        ]

    return app


def run_server(config: RavenConfig | None = None) -> None:
    """Run the API server with uvicorn."""
    import uvicorn

    if config is None:
        config = RavenConfig(working_dir="~/my-knowledge")
    app = create_app(config)
    uvicorn.run(app, host=config.api_host, port=config.api_port)
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/test_api.py -v
```
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "feat: add FastAPI server with ask, ingest, status, and discovery endpoints"
```

---

## Task 10: TypeScript Backend Scaffolding (`openraven-ui` repo)

**Files:**
- Create: `openraven-ui/package.json`
- Create: `openraven-ui/tsconfig.json`
- Create: `openraven-ui/server/index.ts`
- Create: `openraven-ui/server/services/core-client.ts`
- Create: `openraven-ui/server/routes/ask.ts`
- Create: `openraven-ui/server/routes/ingest.ts`
- Create: `openraven-ui/server/routes/status.ts`
- Create: `openraven-ui/server/routes/discovery.ts`

- [ ] **Step 1: Create repo and initialize**

```bash
cd /home/ubuntu/source/OpenRaven
mkdir openraven-ui && cd openraven-ui
git init
```

- [ ] **Step 2: Create package.json**

```json
{
  "name": "openraven-ui",
  "version": "0.1.0",
  "type": "module",
  "scripts": {
    "dev": "concurrently \"bun run dev:server\" \"bun run dev:client\"",
    "dev:server": "bun --watch server/index.ts",
    "dev:client": "vite",
    "build": "vite build",
    "preview": "vite preview",
    "test": "bun test",
    "lint": "tsc --noEmit && eslint ."
  },
  "dependencies": {
    "hono": "^4.0.0",
    "react": "^19.0.0",
    "react-dom": "^19.0.0",
    "react-router-dom": "^7.0.0"
  },
  "devDependencies": {
    "@types/bun": "latest",
    "@types/react": "^19.0.0",
    "@types/react-dom": "^19.0.0",
    "@vitejs/plugin-react": "^4.0.0",
    "@tailwindcss/vite": "^4.0.0",
    "concurrently": "^9.0.0",
    "tailwindcss": "^4.0.0",
    "typescript": "^5.7.0",
    "vite": "^6.0.0"
  }
}
```

- [ ] **Step 3: Create tsconfig.json**

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "ESNext",
    "moduleResolution": "bundler",
    "jsx": "react-jsx",
    "strict": true,
    "esModuleInterop": true,
    "skipLibCheck": true,
    "outDir": "dist",
    "rootDir": ".",
    "baseUrl": ".",
    "paths": {
      "@/*": ["src/*"],
      "@server/*": ["server/*"]
    }
  },
  "include": ["src", "server"]
}
```

- [ ] **Step 4: Implement core client (HTTP client to Python API)**

```typescript
// openraven-ui/server/services/core-client.ts

const CORE_API_URL = process.env.CORE_API_URL ?? "http://127.0.0.1:8741";

export interface StatusResponse {
  total_files: number;
  total_entities: number;
  total_connections: number;
  topic_count: number;
  top_topics: string[];
  confidence_avg: number;
}

export interface AskResponse {
  answer: string;
  mode: string;
}

export interface IngestResponse {
  files_processed: number;
  entities_extracted: number;
  articles_generated: number;
  errors: string[];
}

export interface DiscoveryInsight {
  insight_type: string;
  title: string;
  description: string;
  related_entities: string[];
}

export async function getStatus(): Promise<StatusResponse> {
  const res = await fetch(`${CORE_API_URL}/api/status`);
  if (!res.ok) throw new Error(`Core API error: ${res.status}`);
  return res.json();
}

export async function askQuestion(
  question: string,
  mode: string = "mix"
): Promise<AskResponse> {
  const res = await fetch(`${CORE_API_URL}/api/ask`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question, mode }),
  });
  if (!res.ok) throw new Error(`Core API error: ${res.status}`);
  return res.json();
}

export async function ingestFiles(formData: FormData): Promise<IngestResponse> {
  const res = await fetch(`${CORE_API_URL}/api/ingest`, {
    method: "POST",
    body: formData,
  });
  if (!res.ok) throw new Error(`Core API error: ${res.status}`);
  return res.json();
}

export async function getDiscoveryInsights(): Promise<DiscoveryInsight[]> {
  const res = await fetch(`${CORE_API_URL}/api/discovery`);
  if (!res.ok) throw new Error(`Core API error: ${res.status}`);
  return res.json();
}
```

- [ ] **Step 5: Implement Hono route files**

```typescript
// openraven-ui/server/routes/ask.ts
import { Hono } from "hono";
import { askQuestion } from "../services/core-client";

const askRouter = new Hono();

askRouter.post("/", async (c) => {
  const { question, mode } = await c.req.json<{
    question: string;
    mode?: string;
  }>();

  if (!question) {
    return c.json({ error: "question is required" }, 400);
  }

  try {
    const result = await askQuestion(question, mode ?? "mix");
    return c.json(result);
  } catch (e) {
    const message = e instanceof Error ? e.message : "Unknown error";
    return c.json({ error: `Core engine error: ${message}` }, 502);
  }
});

export default askRouter;
```

```typescript
// openraven-ui/server/routes/ingest.ts
import { Hono } from "hono";
import { ingestFiles } from "../services/core-client";

const ingestRouter = new Hono();

ingestRouter.post("/", async (c) => {
  const body = await c.req.formData();
  const coreForm = new FormData();

  for (const [key, value] of body.entries()) {
    if (value instanceof File) {
      coreForm.append("files", value);
    }
  }

  const result = await ingestFiles(coreForm);
  return c.json(result);
});

export default ingestRouter;
```

```typescript
// openraven-ui/server/routes/status.ts
import { Hono } from "hono";
import { getStatus } from "../services/core-client";

const statusRouter = new Hono();

statusRouter.get("/", async (c) => {
  try {
    const status = await getStatus();
    return c.json(status);
  } catch (e) {
    const message = e instanceof Error ? e.message : "Unknown error";
    return c.json({ error: `Core engine error: ${message}` }, 502);
  }
});

export default statusRouter;
```

```typescript
// openraven-ui/server/routes/discovery.ts
import { Hono } from "hono";
import { getDiscoveryInsights } from "../services/core-client";

const discoveryRouter = new Hono();

discoveryRouter.get("/", async (c) => {
  try {
    const insights = await getDiscoveryInsights();
    return c.json(insights);
  } catch (e) {
    // Discovery is non-critical — return empty rather than error
    return c.json([]);
  }
});

export default discoveryRouter;
```

- [ ] **Step 6: Implement Hono server entry point**

```typescript
// openraven-ui/server/index.ts
import { Hono } from "hono";
import { cors } from "hono/cors";
import { logger } from "hono/logger";

import askRouter from "./routes/ask";
import ingestRouter from "./routes/ingest";
import statusRouter from "./routes/status";
import discoveryRouter from "./routes/discovery";

const app = new Hono();

app.use("*", logger());
app.use(
  "*",
  cors({
    origin: ["http://localhost:5173"],
  })
);

app.get("/health", (c) => c.json({ status: "ok", version: "0.1.0" }));

app.route("/api/ask", askRouter);
app.route("/api/ingest", ingestRouter);
app.route("/api/status", statusRouter);
app.route("/api/discovery", discoveryRouter);

const port = Number(process.env.PORT ?? 3000);
console.log(`OpenRaven UI server running on http://localhost:${port}`);

export default {
  port,
  fetch: app.fetch,
};
```

- [ ] **Step 7: Install dependencies and verify**

```bash
bun install
bun run server/index.ts
# In another terminal: curl http://localhost:3000/health
```
Expected: `{"status":"ok","version":"0.1.0"}`

- [ ] **Step 8: Commit**

```bash
git add -A
git commit -m "feat: scaffold openraven-ui with Hono server proxying to Python core API"
```

---

## Task 11: Minimal Web UI (React + Vite + Tailwind)

**Files:**
- Create: `openraven-ui/index.html`
- Create: `openraven-ui/vite.config.ts`
- Create: `openraven-ui/src/main.tsx`
- Create: `openraven-ui/src/App.tsx`
- Create: `openraven-ui/src/index.css`
- Create: `openraven-ui/src/pages/AskPage.tsx`
- Create: `openraven-ui/src/pages/StatusPage.tsx`
- Create: `openraven-ui/src/pages/IngestPage.tsx`
- Create: `openraven-ui/src/components/ChatMessage.tsx`
- Create: `openraven-ui/src/components/FileUploader.tsx`
- Create: `openraven-ui/src/components/DiscoveryCard.tsx`
- Create: `openraven-ui/src/components/SourceCitation.tsx`

- [ ] **Step 1: Create Vite config with API proxy**

```typescript
// openraven-ui/vite.config.ts
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import path from "path";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "src"),
    },
  },
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: "http://localhost:3000",
        changeOrigin: true,
      },
    },
  },
});
```

- [ ] **Step 2: Create HTML entry point**

```html
<!-- openraven-ui/index.html -->
<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>OpenRaven</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

- [ ] **Step 3: Create main.tsx and App.tsx with routing**

```tsx
// openraven-ui/src/main.tsx
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import App from "./App";
import "./index.css";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </StrictMode>
);
```

```tsx
// openraven-ui/src/App.tsx
import { Routes, Route, NavLink } from "react-router-dom";
import AskPage from "./pages/AskPage";
import StatusPage from "./pages/StatusPage";
import IngestPage from "./pages/IngestPage";

export default function App() {
  return (
    <div className="min-h-screen bg-gray-950 text-gray-100">
      <nav className="border-b border-gray-800 px-6 py-3 flex items-center gap-6">
        <span className="text-lg font-bold text-white tracking-tight">
          OpenRaven
        </span>
        <NavLink
          to="/"
          className={({ isActive }) =>
            isActive ? "text-blue-400" : "text-gray-400 hover:text-gray-200"
          }
        >
          Ask
        </NavLink>
        <NavLink
          to="/ingest"
          className={({ isActive }) =>
            isActive ? "text-blue-400" : "text-gray-400 hover:text-gray-200"
          }
        >
          Add Files
        </NavLink>
        <NavLink
          to="/status"
          className={({ isActive }) =>
            isActive ? "text-blue-400" : "text-gray-400 hover:text-gray-200"
          }
        >
          Status
        </NavLink>
      </nav>
      <main className="max-w-4xl mx-auto px-6 py-8">
        <Routes>
          <Route path="/" element={<AskPage />} />
          <Route path="/ingest" element={<IngestPage />} />
          <Route path="/status" element={<StatusPage />} />
        </Routes>
      </main>
    </div>
  );
}
```

- [ ] **Step 4: Create index.css with Tailwind**

```css
/* openraven-ui/src/index.css */
@import "tailwindcss";
```

- [ ] **Step 5: Implement AskPage (chat-style Q&A)**

```tsx
// openraven-ui/src/pages/AskPage.tsx
import { useState, useRef, useEffect } from "react";
import ChatMessage from "../components/ChatMessage";
import DiscoveryCard from "../components/DiscoveryCard";

interface Message {
  role: "user" | "assistant";
  content: string;
}

interface Insight {
  insight_type: string;
  title: string;
  description: string;
  related_entities: string[];
}

export default function AskPage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [insights, setInsights] = useState<Insight[]>([]);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    fetch("/api/discovery")
      .then((r) => r.json())
      .then(setInsights)
      .catch(() => {});
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!input.trim() || loading) return;

    const question = input.trim();
    setInput("");
    setMessages((prev) => [...prev, { role: "user", content: question }]);
    setLoading(true);

    try {
      const res = await fetch("/api/ask", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question, mode: "mix" }),
      });
      const data = await res.json();
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: data.answer },
      ]);
    } catch {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: "Error: Could not reach the knowledge engine." },
      ]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex flex-col h-[calc(100vh-8rem)]">
      {messages.length === 0 && insights.length > 0 && (
        <div className="mb-6">
          <h2 className="text-sm font-medium text-gray-500 mb-3">
            Discoveries from your knowledge base
          </h2>
          <div className="grid gap-3">
            {insights.map((insight, i) => (
              <DiscoveryCard key={i} insight={insight} />
            ))}
          </div>
        </div>
      )}

      <div className="flex-1 overflow-y-auto space-y-4 pb-4">
        {messages.map((msg, i) => (
          <ChatMessage key={i} role={msg.role} content={msg.content} />
        ))}
        {loading && (
          <div className="text-gray-500 text-sm animate-pulse">Thinking...</div>
        )}
        <div ref={bottomRef} />
      </div>

      <form onSubmit={handleSubmit} className="flex gap-3 pt-4 border-t border-gray-800">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask your knowledge base..."
          className="flex-1 bg-gray-900 border border-gray-700 rounded-lg px-4 py-2.5 text-gray-100 placeholder-gray-500 focus:outline-none focus:border-blue-500"
        />
        <button
          type="submit"
          disabled={loading || !input.trim()}
          className="bg-blue-600 hover:bg-blue-500 disabled:bg-gray-700 disabled:text-gray-500 text-white px-5 py-2.5 rounded-lg font-medium transition-colors"
        >
          Ask
        </button>
      </form>
    </div>
  );
}
```

- [ ] **Step 6: Implement IngestPage (file upload)**

```tsx
// openraven-ui/src/pages/IngestPage.tsx
import { useState } from "react";
import FileUploader from "../components/FileUploader";

interface IngestResult {
  files_processed: number;
  entities_extracted: number;
  articles_generated: number;
  errors: string[];
}

export default function IngestPage() {
  const [result, setResult] = useState<IngestResult | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleUpload(files: File[]) {
    setLoading(true);
    setResult(null);

    const formData = new FormData();
    for (const file of files) {
      formData.append("files", file);
    }

    try {
      const res = await fetch("/api/ingest", {
        method: "POST",
        body: formData,
      });
      const data = await res.json();
      setResult(data);
    } catch {
      setResult({
        files_processed: 0,
        entities_extracted: 0,
        articles_generated: 0,
        errors: ["Failed to connect to the knowledge engine."],
      });
    } finally {
      setLoading(false);
    }
  }

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Add Documents</h1>
      <FileUploader onUpload={handleUpload} disabled={loading} />

      {loading && (
        <div className="mt-6 text-gray-400 animate-pulse">
          Processing documents... This may take a few minutes.
        </div>
      )}

      {result && (
        <div className="mt-6 bg-gray-900 border border-gray-800 rounded-lg p-4">
          <h2 className="font-semibold mb-2">Results</h2>
          <div className="grid grid-cols-3 gap-4 text-center">
            <div>
              <div className="text-2xl font-bold text-blue-400">
                {result.files_processed}
              </div>
              <div className="text-xs text-gray-500">Files processed</div>
            </div>
            <div>
              <div className="text-2xl font-bold text-green-400">
                {result.entities_extracted}
              </div>
              <div className="text-xs text-gray-500">Entities extracted</div>
            </div>
            <div>
              <div className="text-2xl font-bold text-purple-400">
                {result.articles_generated}
              </div>
              <div className="text-xs text-gray-500">Articles generated</div>
            </div>
          </div>
          {result.errors.length > 0 && (
            <div className="mt-3 text-red-400 text-sm">
              {result.errors.map((e, i) => (
                <div key={i}>{e}</div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 7: Implement StatusPage**

```tsx
// openraven-ui/src/pages/StatusPage.tsx
import { useEffect, useState } from "react";

interface Status {
  total_files: number;
  total_entities: number;
  total_connections: number;
  topic_count: number;
  top_topics: string[];
  confidence_avg: number;
}

export default function StatusPage() {
  const [status, setStatus] = useState<Status | null>(null);

  useEffect(() => {
    fetch("/api/status")
      .then((r) => r.json())
      .then(setStatus)
      .catch(() => {});
  }, []);

  if (!status) {
    return <div className="text-gray-500">Loading...</div>;
  }

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Knowledge Base Status</h1>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
        {[
          { label: "Files", value: status.total_files, color: "text-blue-400" },
          { label: "Concepts", value: status.total_entities, color: "text-green-400" },
          { label: "Connections", value: status.total_connections, color: "text-purple-400" },
          { label: "Topics", value: status.topic_count, color: "text-amber-400" },
        ].map((stat) => (
          <div
            key={stat.label}
            className="bg-gray-900 border border-gray-800 rounded-lg p-4 text-center"
          >
            <div className={`text-3xl font-bold ${stat.color}`}>{stat.value}</div>
            <div className="text-xs text-gray-500 mt-1">{stat.label}</div>
          </div>
        ))}
      </div>

      {status.top_topics.length > 0 && (
        <div>
          <h2 className="text-lg font-semibold mb-3">Top Topics</h2>
          <div className="flex flex-wrap gap-2">
            {status.top_topics.map((topic) => (
              <span
                key={topic}
                className="bg-gray-800 border border-gray-700 rounded-full px-3 py-1 text-sm text-gray-300"
              >
                {topic}
              </span>
            ))}
          </div>
        </div>
      )}

      {status.confidence_avg > 0 && (
        <div className="mt-6 text-sm text-gray-400">
          Average confidence: {(status.confidence_avg * 100).toFixed(0)}%
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 8: Implement shared components**

```tsx
// openraven-ui/src/components/ChatMessage.tsx
import SourceCitation from "./SourceCitation";

interface Props {
  role: "user" | "assistant";
  content: string;
}

/**
 * Parse [Source: document.md:123-456] markers from assistant content
 * and render them as clickable SourceCitation components.
 */
function renderContentWithCitations(content: string) {
  // Match patterns like [Source: filename.md] or [Source: filename.md:100-200]
  const sourcePattern = /\[Source:\s*([^\]]+?)(?::(\d+)-(\d+))?\]/g;
  const parts: (string | { document: string; charStart?: number; charEnd?: number })[] = [];
  let lastIndex = 0;

  for (const match of content.matchAll(sourcePattern)) {
    if (match.index! > lastIndex) {
      parts.push(content.slice(lastIndex, match.index!));
    }
    parts.push({
      document: match[1].trim(),
      charStart: match[2] ? Number(match[2]) : undefined,
      charEnd: match[3] ? Number(match[3]) : undefined,
    });
    lastIndex = match.index! + match[0].length;
  }
  if (lastIndex < content.length) {
    parts.push(content.slice(lastIndex));
  }

  return parts.map((part, i) =>
    typeof part === "string" ? (
      <span key={i}>{part}</span>
    ) : (
      <SourceCitation
        key={i}
        document={part.document}
        excerpt=""
        charStart={part.charStart}
        charEnd={part.charEnd}
      />
    )
  );
}

export default function ChatMessage({ role, content }: Props) {
  return (
    <div
      className={`flex ${role === "user" ? "justify-end" : "justify-start"}`}
    >
      <div
        className={`max-w-[80%] rounded-lg px-4 py-2.5 text-sm leading-relaxed ${
          role === "user"
            ? "bg-blue-600 text-white"
            : "bg-gray-800 text-gray-200 border border-gray-700"
        }`}
      >
        <div className="whitespace-pre-wrap">
          {role === "assistant" ? renderContentWithCitations(content) : content}
        </div>
      </div>
    </div>
  );
}
```

```tsx
// openraven-ui/src/components/FileUploader.tsx
import { useCallback } from "react";

interface Props {
  onUpload: (files: File[]) => void;
  disabled?: boolean;
}

export default function FileUploader({ onUpload, disabled }: Props) {
  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      if (disabled) return;
      const files = Array.from(e.dataTransfer.files);
      if (files.length > 0) onUpload(files);
    },
    [onUpload, disabled]
  );

  const handleChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const files = Array.from(e.target.files ?? []);
      if (files.length > 0) onUpload(files);
    },
    [onUpload]
  );

  return (
    <div
      onDrop={handleDrop}
      onDragOver={(e) => e.preventDefault()}
      className={`border-2 border-dashed rounded-lg p-12 text-center transition-colors ${
        disabled
          ? "border-gray-800 text-gray-600"
          : "border-gray-700 text-gray-400 hover:border-blue-500 hover:text-blue-400 cursor-pointer"
      }`}
    >
      <p className="text-lg mb-2">Drop files here</p>
      <p className="text-sm mb-4">PDF, DOCX, PPTX, XLSX, Markdown, TXT</p>
      <label
        className={`inline-block px-4 py-2 rounded-lg text-sm font-medium ${
          disabled
            ? "bg-gray-800 text-gray-600"
            : "bg-gray-800 text-gray-300 hover:bg-gray-700 cursor-pointer"
        }`}
      >
        Browse files
        <input
          type="file"
          multiple
          onChange={handleChange}
          disabled={disabled}
          className="hidden"
          accept=".pdf,.docx,.pptx,.xlsx,.md,.txt,.html"
        />
      </label>
    </div>
  );
}
```

```tsx
// openraven-ui/src/components/DiscoveryCard.tsx
interface Insight {
  insight_type: string;
  title: string;
  description: string;
  related_entities: string[];
}

interface Props {
  insight: Insight;
}

const TYPE_COLORS: Record<string, string> = {
  theme: "border-blue-500/30 bg-blue-500/5",
  cluster: "border-green-500/30 bg-green-500/5",
  gap: "border-amber-500/30 bg-amber-500/5",
  trend: "border-purple-500/30 bg-purple-500/5",
};

export default function DiscoveryCard({ insight }: Props) {
  const colorClass = TYPE_COLORS[insight.insight_type] ?? TYPE_COLORS.theme;

  return (
    <div className={`border rounded-lg p-4 ${colorClass}`}>
      <div className="flex items-center gap-2 mb-1">
        <span className="text-xs uppercase tracking-wider text-gray-500">
          {insight.insight_type}
        </span>
      </div>
      <h3 className="font-medium text-gray-200">{insight.title}</h3>
      <p className="text-sm text-gray-400 mt-1">{insight.description}</p>
      {insight.related_entities.length > 0 && (
        <div className="flex flex-wrap gap-1.5 mt-2">
          {insight.related_entities.slice(0, 5).map((entity) => (
            <span
              key={entity}
              className="text-xs bg-gray-800 rounded px-2 py-0.5 text-gray-400"
            >
              {entity}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
```

```tsx
// openraven-ui/src/components/SourceCitation.tsx
interface Props {
  document: string;
  excerpt: string;
  charStart?: number;
  charEnd?: number;
}

export default function SourceCitation({
  document,
  excerpt,
  charStart,
  charEnd,
}: Props) {
  const location =
    charStart != null && charEnd != null ? ` (chars ${charStart}-${charEnd})` : "";

  return (
    <div className="border-l-2 border-gray-700 pl-3 py-1 my-2 text-xs text-gray-500">
      <span className="font-medium text-gray-400">{document}</span>
      {location}
      <p className="italic mt-0.5">{excerpt}</p>
    </div>
  );
}
```

- [ ] **Step 9: Verify build**

```bash
bun run build
```
Expected: Vite build succeeds

- [ ] **Step 10: Commit**

```bash
git add -A
git commit -m "feat: add minimal Web UI with Ask, Ingest, and Status pages"
```

---

## Task 12: Integration Testing & End-to-End Verification

**Files:**
- Create: `openraven/tests/test_integration.py`
- Create: `openraven/scripts/smoke_test.sh`

- [ ] **Step 1: Create integration test (requires API keys)**

```python
# openraven/tests/test_integration.py
"""Integration tests — require GEMINI_API_KEY and ANTHROPIC_API_KEY env vars.

Run with: pytest tests/test_integration.py -v --run-integration
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest

from openraven.config import RavenConfig
from openraven.pipeline import RavenPipeline

pytestmark = pytest.mark.skipif(
    not os.environ.get("GEMINI_API_KEY"),
    reason="GEMINI_API_KEY not set — skipping integration tests",
)


@pytest.fixture
def integration_config(tmp_path: Path) -> RavenConfig:
    return RavenConfig(
        working_dir=tmp_path / "integration_kb",
        llm_model="gemini-2.5-flash",
        wiki_llm_model="claude-sonnet-4-6",
    )


@pytest.fixture
def pipeline(integration_config: RavenConfig) -> RavenPipeline:
    return RavenPipeline(integration_config)


async def test_full_pipeline_english(pipeline: RavenPipeline, tmp_path: Path) -> None:
    """Test full pipeline with an English engineering document."""
    doc = tmp_path / "adr-001.md"
    doc.write_text("""\
# ADR-001: Use PostgreSQL for Primary Database

## Status: Accepted

## Context
We need a primary database for the user service. Evaluated PostgreSQL, MySQL, and MongoDB.
PostgreSQL offers strong ACID compliance, JSONB for flexible schemas, and mature ecosystem.

## Decision
Use PostgreSQL 16 with pgvector extension for future vector search needs.

## Consequences
- Positive: Strong typing, excellent query planner, JSONB flexibility
- Negative: Slightly higher memory usage than MySQL
- Risk: Team needs PostgreSQL-specific training
""")

    result = await pipeline.add_files([doc])
    assert result.files_processed == 1
    assert result.entities_extracted > 0

    # Test Q&A
    answer = await pipeline.ask("What database was chosen and why?")
    assert "PostgreSQL" in answer or "postgresql" in answer.lower()


async def test_full_pipeline_chinese(pipeline: RavenPipeline, tmp_path: Path) -> None:
    """Test full pipeline with a Traditional Chinese finance document."""
    doc = tmp_path / "research-tsmc.md"
    doc.write_text("""\
# 台積電（2330）投資研究筆記

## 基本面分析
台積電 2026 年第一季營收達 8,692 億元，年增 35%。
先進製程（7nm 以下）佔營收 73%。

## 技術優勢
- 3nm 良率已達 80% 以上
- CoWoS 先進封裝產能持續擴充
- NVIDIA、Apple 為最大客戶

## 風險評估
地緣政治風險仍是最大不確定因素。
美國亞利桑那廠進度略為落後。
""")

    result = await pipeline.add_files([doc])
    assert result.files_processed == 1
    assert result.entities_extracted > 0

    answer = await pipeline.ask("台積電的先進製程佔營收比例是多少？")
    assert "73" in answer or "先進製程" in answer
```

- [ ] **Step 2: Create smoke test script**

```bash
#!/usr/bin/env bash
# openraven/scripts/smoke_test.sh
# Quick smoke test for the full pipeline
set -euo pipefail

echo "=== OpenRaven Smoke Test ==="

WORKING_DIR=$(mktemp -d)
echo "Working dir: $WORKING_DIR"

# Create test document
cat > "$WORKING_DIR/test_doc.md" << 'EOF'
# Technical Decision: Migrate to Kubernetes

We decided to migrate from EC2 instances to Kubernetes (EKS) for container orchestration.
Key reasons: auto-scaling, self-healing, and declarative infrastructure.
Trade-off: increased operational complexity and learning curve for the team.
EOF

echo ""
echo "1. Initialize knowledge base..."
raven init "$WORKING_DIR/kb"

echo ""
echo "2. Add document..."
raven add "$WORKING_DIR/test_doc.md" -w "$WORKING_DIR/kb"

echo ""
echo "3. Ask question..."
raven ask "What was the migration decision?" -w "$WORKING_DIR/kb"

echo ""
echo "4. Check status..."
raven status -w "$WORKING_DIR/kb"

echo ""
echo "=== Smoke Test Complete ==="
rm -rf "$WORKING_DIR"
```

- [ ] **Step 3: Make script executable and test**

```bash
chmod +x scripts/smoke_test.sh
# Run only if API keys are set:
# ./scripts/smoke_test.sh
```

- [ ] **Step 4: Run unit tests (no API key needed)**

```bash
pytest tests/ -v --ignore=tests/test_integration.py
```
Expected: All unit tests PASS

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "feat: add integration tests and smoke test script"
```

---

## Milestone Summary

After completing all 12 tasks, M1 delivers:

| Component | Status |
|-----------|--------|
| Document ingestion (Docling) | PDF, DOCX, PPTX, XLSX, MD, TXT |
| Entity extraction (LangExtract) | With source grounding, engineering + finance schemas |
| Knowledge graph (LightRAG) | NetworkX + NanoVectorDB, 6 query modes |
| Wiki article generation | Claude-powered, with source citations |
| Proactive discovery | Theme analysis, "first surprise moment" |
| Health reporter | Stats and coverage report |
| Pipeline orchestrator | 4-stage, incremental updates |
| CLI tool (`raven`) | init, add, ask, status, graph, export |
| Python API (FastAPI) | REST endpoints for UI integration |
| TypeScript backend (Hono) | Proxy to Python API |
| Minimal Web UI (React) | Ask, Ingest, Status pages |
| Integration tests | English + Chinese document tests |

**What's deferred to M2:**
- Ollama local LLM support
- Chrome extension
- Knowledge graph visualization (interactive)
- Cloud sync (E2EE)
- Google Drive / Gmail connectors
