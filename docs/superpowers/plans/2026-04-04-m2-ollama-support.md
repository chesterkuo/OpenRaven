# Ollama Local LLM Support Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add Ollama as a local LLM/embedding backend so OpenRaven can run with zero data leakage — no API keys required, all processing stays on-device.

**Architecture:** The `llm_provider` field in `RavenConfig` (currently dead) becomes the dispatch key. When set to `"ollama"`, the three LLM call sites (LightRAG LLM, LightRAG embedding, LangExtract extraction, wiki compilation) all route to local Ollama. LangExtract already has native Ollama support via model_id pattern matching. LightRAG has `ollama_model_complete` and `ollama_embed`. Wiki compiler uses OpenAI-compat client which Ollama also serves at `/v1`. The config reads from env vars (`OPENRAVEN_LLM_PROVIDER`, `OPENRAVEN_LLM_MODEL`, etc.) so switching providers is a `.env` change + PM2 restart.

**Tech Stack:**
- Python: LightRAG's `lightrag.llm.ollama` (already installed), LangExtract's `OllamaLanguageModel` (already installed)
- Ollama server: user-installed, default `http://localhost:11434`
- No new Python packages needed

**PRD Alignment:**
- Implements "本地 Ollama 全功能" (P0, M2 acceptance: all features 100% on Ollama)
- Enables "零資料外洩" (zero data leakage) mode

---

## File Structure

### Python backend (openraven/)

| File | Action | Responsibility |
|---|---|---|
| `src/openraven/config.py` | Modify | Add `ollama_base_url`, wire env var overrides, make `llm_provider` functional |
| `src/openraven/graph/rag.py` | Modify | Add Ollama branches in `_make_llm_func` and `_make_embedding_func` |
| `src/openraven/wiki/compiler.py` | Modify | Parameterize `base_url` in `compile_article`, add Ollama endpoint support |
| `src/openraven/pipeline.py` | Modify | Pass provider-aware config to all three subsystems |
| `src/openraven/api/server.py` | Modify | Expose provider info in `/api/status`, add `GET /api/config/provider` |
| `.env.example` | Modify | Document Ollama env vars |
| `tests/test_config.py` | Create | Test config env var loading and provider dispatch |
| `tests/test_graph.py` | Modify | Test Ollama branch creation in `_make_llm_func` and `_make_embedding_func` |
| `tests/test_wiki.py` | Modify | Test `compile_article` with custom `base_url` |

### TypeScript frontend (openraven-ui/)

| File | Action | Responsibility |
|---|---|---|
| `server/services/core-client.ts` | Modify | Add `getProviderInfo()` type + function |
| `src/pages/StatusPage.tsx` | Modify | Show current LLM provider name |

---

## Task 1: Config — env var overrides and Ollama fields

**Files:**
- Modify: `openraven/src/openraven/config.py`
- Create: `openraven/tests/test_config.py`

- [ ] **Step 1: Write failing tests**

Create `openraven/tests/test_config.py`:

```python
from __future__ import annotations

import os

from openraven.config import RavenConfig


def test_default_provider_is_gemini(tmp_path) -> None:
    config = RavenConfig(working_dir=tmp_path / "kb")
    assert config.llm_provider == "gemini"
    assert config.ollama_base_url == "http://localhost:11434"


def test_env_var_overrides(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("OPENRAVEN_LLM_PROVIDER", "ollama")
    monkeypatch.setenv("OPENRAVEN_LLM_MODEL", "llama3.2:3b")
    monkeypatch.setenv("OPENRAVEN_WIKI_MODEL", "llama3.2:3b")
    monkeypatch.setenv("OPENRAVEN_EMBEDDING_MODEL", "nomic-embed-text")
    monkeypatch.setenv("OPENRAVEN_OLLAMA_URL", "http://gpu-box:11434")

    config = RavenConfig(working_dir=tmp_path / "kb")
    assert config.llm_provider == "ollama"
    assert config.llm_model == "llama3.2:3b"
    assert config.wiki_llm_model == "llama3.2:3b"
    assert config.embedding_model == "nomic-embed-text"
    assert config.ollama_base_url == "http://gpu-box:11434"


def test_explicit_args_override_env(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("OPENRAVEN_LLM_PROVIDER", "ollama")
    config = RavenConfig(working_dir=tmp_path / "kb", llm_provider="gemini")
    assert config.llm_provider == "gemini"


def test_api_key_property(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "test-key-123")
    config = RavenConfig(working_dir=tmp_path / "kb")
    assert config.llm_api_key == "test-key-123"


def test_api_key_empty_for_ollama(tmp_path) -> None:
    config = RavenConfig(working_dir=tmp_path / "kb", llm_provider="ollama")
    assert config.llm_api_key == ""
```

- [ ] **Step 2: Run to verify failure**

Run: `cd openraven && .venv/bin/python -m pytest tests/test_config.py -v`
Expected: FAIL (missing `ollama_base_url`, `llm_api_key`, env var logic)

- [ ] **Step 3: Implement config changes**

Replace `openraven/src/openraven/config.py`:

```python
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
```

- [ ] **Step 4: Run tests**

Run: `cd openraven && .venv/bin/python -m pytest tests/test_config.py -v`
Expected: 5 tests PASS

- [ ] **Step 5: Run all tests for regression**

Run: `cd openraven && .venv/bin/python -m pytest tests/ -v --ignore=tests/test_integration.py`
Expected: All pass

- [ ] **Step 6: Commit**

```bash
git add openraven/src/openraven/config.py openraven/tests/test_config.py
git commit -m "feat(config): add Ollama fields and env var overrides to RavenConfig"
```

---

## Task 2: RavenGraph — Ollama LLM and embedding branches

**Files:**
- Modify: `openraven/src/openraven/graph/rag.py`
- Modify: `openraven/tests/test_graph.py`

- [ ] **Step 1: Write failing tests**

Add to `openraven/tests/test_graph.py`:

```python
def test_make_llm_func_gemini() -> None:
    func = RavenGraph._make_llm_func("gemini-2.5-flash", "test-key", provider="gemini")
    assert callable(func)


def test_make_llm_func_ollama() -> None:
    func = RavenGraph._make_llm_func("llama3.2:3b", "", provider="ollama")
    assert callable(func)


def test_make_embedding_func_gemini() -> None:
    ef = RavenGraph._make_embedding_func("text-embedding-004", "test-key", provider="gemini")
    assert ef.embedding_dim == 768


def test_make_embedding_func_ollama() -> None:
    ef = RavenGraph._make_embedding_func("nomic-embed-text", "", provider="ollama")
    assert ef.embedding_dim == 768


def test_make_embedding_func_ollama_1024() -> None:
    ef = RavenGraph._make_embedding_func("bge-m3:latest", "", provider="ollama")
    assert ef.embedding_dim == 1024
```

- [ ] **Step 2: Run to verify failure**

Run: `cd openraven && .venv/bin/python -m pytest tests/test_graph.py -v -k "make_llm_func or make_embedding_func"`
Expected: FAIL (unexpected keyword argument `provider`)

- [ ] **Step 3: Implement Ollama branches**

Modify `openraven/src/openraven/graph/rag.py`:

In `create` and `create_lazy`, add `provider` and `ollama_base_url` parameters:

```python
@classmethod
async def create(
    cls,
    working_dir: Path,
    llm_model: str = "gemini-2.5-flash",
    llm_api_key: str | None = None,
    embedding_model: str = "text-embedding-004",
    provider: str = "gemini",
    ollama_base_url: str = "http://localhost:11434",
) -> RavenGraph:
    if not LIGHTRAG_AVAILABLE:
        raise ImportError("lightrag-hku is not installed")
    working_dir = Path(working_dir)
    working_dir.mkdir(parents=True, exist_ok=True)
    llm_func = cls._make_llm_func(llm_model, llm_api_key, provider=provider, ollama_base_url=ollama_base_url)
    embed_func = cls._make_embedding_func(embedding_model, llm_api_key, provider=provider, ollama_base_url=ollama_base_url)
    rag = LightRAG(
        working_dir=str(working_dir),
        llm_model_func=llm_func,
        llm_model_name=llm_model,
        embedding_func=embed_func,
    )
    await rag.initialize_storages()
    instance = cls(working_dir, rag)
    instance._initialized = True
    return instance
```

Apply the same pattern to `create_lazy`.

Update `_make_llm_func`:

```python
@staticmethod
def _make_llm_func(model, api_key, provider="gemini", ollama_base_url="http://localhost:11434"):
    import os
    from functools import partial

    if provider == "ollama":
        from lightrag.llm.ollama import ollama_model_complete
        return ollama_model_complete

    from lightrag.llm.openai import openai_complete_if_cache

    if "gemini" in model:
        key = api_key or os.environ.get("GEMINI_API_KEY", "")
        return partial(
            openai_complete_if_cache,
            model,
            api_key=key,
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
        )
    key = api_key or os.environ.get("OPENAI_API_KEY", "")
    return partial(openai_complete_if_cache, model, api_key=key)
```

Update `_make_embedding_func`:

```python
@staticmethod
def _make_embedding_func(model, api_key, provider="gemini", ollama_base_url="http://localhost:11434"):
    import os
    from functools import partial

    from lightrag.utils import EmbeddingFunc

    if provider == "ollama":
        from lightrag.llm.ollama import ollama_embed

        # nomic-embed-text: 768 dims, bge-m3/mxbai-embed-large: 1024 dims
        dim = 768 if "nomic" in model else 1024
        raw_ollama_embed = ollama_embed.func  # bypass decorator's validator

        async def _ollama_embed(texts, **kwargs):
            return await raw_ollama_embed(texts, embed_model=model, host=ollama_base_url, **kwargs)

        return EmbeddingFunc(
            embedding_dim=dim,
            func=_ollama_embed,
            model_name=model,
        )

    # Gemini path (existing)
    key = api_key or os.environ.get("GEMINI_API_KEY", "")

    if "gemini" in model or "text-embedding" in model:
        from lightrag.llm.gemini import gemini_embed

        embed_model = "gemini-embedding-001"
        raw_gemini_embed = gemini_embed.func

        base_func = partial(raw_gemini_embed, model=embed_model, api_key=key)

        async def _safe_gemini_embed(texts, **kwargs):
            import numpy as np
            kwargs.setdefault("embedding_dim", 768)
            result = await base_func(texts, **kwargs)
            expected = len(texts)
            if result.shape[0] > expected:
                result = result[:expected]
            return result

        return EmbeddingFunc(
            embedding_dim=768,
            func=_safe_gemini_embed,
            model_name=embed_model,
        )

    from lightrag.llm.openai import openai_embed

    return EmbeddingFunc(
        embedding_dim=1536,
        func=partial(openai_embed, model=model),
        model_name=model,
    )
```

- [ ] **Step 4: Run tests**

Run: `cd openraven && .venv/bin/python -m pytest tests/test_graph.py -v`
Expected: All pass (existing + 5 new)

- [ ] **Step 5: Run all tests**

Run: `cd openraven && .venv/bin/python -m pytest tests/ -v --ignore=tests/test_integration.py`

- [ ] **Step 6: Commit**

```bash
git add openraven/src/openraven/graph/rag.py openraven/tests/test_graph.py
git commit -m "feat(graph): add Ollama LLM and embedding branches to RavenGraph"
```

---

## Task 3: Wiki compiler — parameterize base_url

**Files:**
- Modify: `openraven/src/openraven/wiki/compiler.py`
- Modify: `openraven/tests/test_wiki.py`

- [ ] **Step 1: Write failing test**

Add to `openraven/tests/test_wiki.py`:

```python
def test_compile_article_accepts_base_url() -> None:
    import inspect
    from openraven.wiki.compiler import compile_article
    sig = inspect.signature(compile_article)
    assert "base_url" in sig.parameters


def test_compile_wiki_for_graph_accepts_base_url() -> None:
    import inspect
    from openraven.wiki.compiler import compile_wiki_for_graph
    sig = inspect.signature(compile_wiki_for_graph)
    assert "base_url" in sig.parameters
```

- [ ] **Step 2: Run to verify failure**

Run: `cd openraven && .venv/bin/python -m pytest tests/test_wiki.py -v -k "base_url"`
Expected: FAIL

- [ ] **Step 3: Add `base_url` parameter**

Modify `compile_article` signature and body in `openraven/src/openraven/wiki/compiler.py`:

```python
async def compile_article(
    topic: str, context: str, sources: list[dict],
    api_key: str, model: str = "claude-sonnet-4-6",
    base_url: str = "https://generativelanguage.googleapis.com/v1beta/openai/",
) -> WikiArticle:
    source_text = "\n".join(
        f"- {s['document']} (chars {s.get('char_start', '?')}-{s.get('char_end', '?')}): "
        f"{s.get('excerpt', '')}"
        for s in sources
    )
    prompt = COMPILE_PROMPT.format(topic=topic, context=context, sources=source_text)

    client = openai.AsyncOpenAI(api_key=api_key or "ollama", base_url=base_url)
    response = await client.chat.completions.create(
        model=model, max_tokens=2000,
        messages=[{"role": "user", "content": prompt}],
    )
    # ... rest unchanged
```

Modify `compile_wiki_for_graph` signature:

```python
async def compile_wiki_for_graph(
    graph, entities: list[str], sources_map: dict, api_key: str,
    output_dir: Path, model: str = "claude-sonnet-4-6", max_concurrent: int = 5,
    on_progress: callable | None = None,
    base_url: str = "https://generativelanguage.googleapis.com/v1beta/openai/",
) -> list[WikiArticle]:
```

And pass `base_url` through to `compile_article` inside `compile_one`:

```python
article = await compile_article(
    topic=entity_name, context=context, sources=sources,
    api_key=api_key, model=model, base_url=base_url,
)
```

- [ ] **Step 4: Run tests**

Run: `cd openraven && .venv/bin/python -m pytest tests/test_wiki.py -v`
Expected: All pass

- [ ] **Step 5: Commit**

```bash
git add openraven/src/openraven/wiki/compiler.py openraven/tests/test_wiki.py
git commit -m "feat(wiki): parameterize base_url for Ollama support"
```

---

## Task 4: Pipeline — wire provider config through all subsystems

**Files:**
- Modify: `openraven/src/openraven/pipeline.py`
- Modify: `openraven/tests/test_pipeline.py`

- [ ] **Step 1: Write failing test**

Add to `openraven/tests/test_pipeline.py`:

```python
def test_pipeline_passes_provider_to_graph(config: RavenConfig) -> None:
    config.llm_provider = "ollama"
    config.llm_model = "llama3.2:3b"
    config.embedding_model = "nomic-embed-text"
    pipeline = RavenPipeline(config)
    # Pipeline should construct without error even with ollama provider
    assert pipeline.graph is not None
```

- [ ] **Step 2: Run to verify failure**

Run: `cd openraven && .venv/bin/python -m pytest tests/test_pipeline.py -v -k "provider"`

- [ ] **Step 3: Update pipeline to pass provider config**

Modify `openraven/src/openraven/pipeline.py`, in `RavenPipeline.__init__`:

```python
self.graph = RavenGraph.create_lazy(
    working_dir=config.lightrag_dir,
    llm_model=config.llm_model,
    llm_api_key=config.llm_api_key,
    provider=config.llm_provider,
    ollama_base_url=config.ollama_base_url,
)
```

In `add_files`, update Stage 2 extraction to pass model from config:

```python
result = await extract_entities(
    text=doc.text, source_document=str(doc.source_path),
    schema=schema, model_id=self.config.llm_model,
)
```

In `add_files`, update wiki compilation to pass base_url:

```python
wiki_base_url = (
    f"{self.config.ollama_base_url}/v1"
    if self.config.llm_provider == "ollama"
    else "https://generativelanguage.googleapis.com/v1beta/openai/"
)
articles = await compile_wiki_for_graph(
    graph=self.graph, entities=entity_names, sources_map=sources_map,
    api_key=self.config.llm_api_key, output_dir=self.config.wiki_dir,
    model=self.config.wiki_llm_model, base_url=wiki_base_url,
)
```

- [ ] **Step 4: Run tests**

Run: `cd openraven && .venv/bin/python -m pytest tests/ -v --ignore=tests/test_integration.py`
Expected: All pass

- [ ] **Step 5: Commit**

```bash
git add openraven/src/openraven/pipeline.py openraven/tests/test_pipeline.py
git commit -m "feat(pipeline): wire provider config to all LLM subsystems"
```

---

## Task 5: API — provider info endpoint + status display

**Files:**
- Modify: `openraven/src/openraven/api/server.py`
- Modify: `openraven/tests/test_api.py`
- Modify: `openraven-ui/src/pages/StatusPage.tsx`

- [ ] **Step 1: Write failing test**

Add to `openraven/tests/test_api.py`:

```python
def test_provider_endpoint(client: TestClient) -> None:
    response = client.get("/api/config/provider")
    assert response.status_code == 200
    data = response.json()
    assert "provider" in data
    assert "llm_model" in data
    assert "embedding_model" in data
```

- [ ] **Step 2: Implement endpoint**

Add to `server.py` inside `create_app()`:

```python
@app.get("/api/config/provider")
async def provider_info():
    return {
        "provider": config.llm_provider,
        "llm_model": config.llm_model,
        "wiki_model": config.wiki_llm_model,
        "embedding_model": config.embedding_model,
        "ollama_url": config.ollama_base_url if config.llm_provider == "ollama" else None,
    }
```

- [ ] **Step 3: Update StatusPage to show provider**

Add to `openraven-ui/src/pages/StatusPage.tsx`, after the status fetch:

```tsx
const [provider, setProvider] = useState<{provider: string; llm_model: string} | null>(null);
useEffect(() => { fetch("/api/config/provider").then(r => r.json()).then(setProvider).catch(() => {}); }, []);
```

Add below the stat tiles:

```tsx
{provider && (
  <div className="mb-8 text-sm text-gray-500">
    LLM: <span className="text-gray-300">{provider.provider}/{provider.llm_model}</span>
  </div>
)}
```

- [ ] **Step 4: Run all tests**

Run: `cd openraven && .venv/bin/python -m pytest tests/ -v --ignore=tests/test_integration.py`
Run: `cd openraven-ui && bun test tests/ && bun run build`

- [ ] **Step 5: Commit**

```bash
git add openraven/src/openraven/api/server.py openraven/tests/test_api.py openraven-ui/src/pages/StatusPage.tsx
git commit -m "feat(api): add provider info endpoint, show provider in status page"
```

---

## Task 6: Update .env.example and verify E2E

**Files:**
- Modify: `openraven/.env.example`

- [ ] **Step 1: Update .env.example**

Replace `openraven/.env.example`:

```bash
# === LLM Provider ===
# Set to "ollama" for local-only mode (zero data leakage)
# Set to "gemini" for Google Gemini cloud API
# OPENRAVEN_LLM_PROVIDER=gemini

# === Gemini (cloud) ===
GEMINI_API_KEY=your-gemini-api-key-here
# ANTHROPIC_API_KEY=your-anthropic-api-key-here

# === Ollama (local) ===
# OPENRAVEN_OLLAMA_URL=http://localhost:11434
# OPENRAVEN_LLM_MODEL=llama3.2:3b
# OPENRAVEN_WIKI_MODEL=llama3.2:3b
# OPENRAVEN_EMBEDDING_MODEL=nomic-embed-text

# === General ===
# OPENRAVEN_WORKING_DIR=~/my-knowledge
```

- [ ] **Step 2: Run full test suite**

```bash
cd openraven && .venv/bin/python -m pytest tests/ -v --ignore=tests/test_integration.py
cd openraven-ui && bun test tests/ && bun run build
```

- [ ] **Step 3: Restart PM2 and verify Gemini still works**

```bash
pm2 restart all
sleep 8
curl -sf http://localhost:8741/api/config/provider | python3 -m json.tool
curl -sf http://localhost:8741/api/status | python3 -m json.tool
```

- [ ] **Step 4: Commit**

```bash
git add openraven/.env.example
git commit -m "docs: update .env.example with Ollama provider configuration"
```

---

## Summary

| Task | What | Tests Added |
|---|---|---|
| 1 | Config env var overrides + Ollama fields | 5 config tests |
| 2 | RavenGraph Ollama LLM + embedding branches | 5 graph tests |
| 3 | Wiki compiler base_url parameterization | 2 wiki tests |
| 4 | Pipeline provider wiring | 1 pipeline test |
| 5 | Provider info API + status display | 1 API test |
| 6 | .env.example + E2E verification | Manual |

**Total new tests: 14**

**Note:** Full Ollama E2E testing requires a running Ollama server with models pulled (`ollama pull llama3.2:3b && ollama pull nomic-embed-text`). These are integration tests that should be run manually, not in CI.
