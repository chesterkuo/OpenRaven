# Ingest Speedup: Template Wiki + Lean Extraction

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Drop ingest pipeline from ~6.5 min/doc to ~45 seconds by (1) replacing LLM-generated wiki articles with graph-templated rendering (kills Stage 3) and (2) replacing LangExtract's chunked Gemini loop with a single-call Gemini JSON extraction plus local offset alignment via rapidfuzz (halves Stage 2).

**Architecture:** Two independent subsystems, each shippable on its own — execute in order but either phase may be released to production alone.

- **Phase 1 — Template Wiki (Stage 3)**: Rewrite `compile_wiki_for_graph` to render each entity's markdown from the graph itself (node attributes + 1-hop neighbors via `RavenGraph.get_subgraph` + source excerpts from the existing `sources_map`). Zero LLM calls. Existing `compile_article()` is kept for a future on-demand "Improve with AI" button but is no longer called from the ingest pipeline.

- **Phase 2 — Single-call Extraction (Stage 2a)**: Replace `_run_langextract` with one `gemini-2.5-flash` call (77K chars fits well inside flash's 1M-token context) returning entities as JSON. Recover `char_start`/`char_end` locally via `rapidfuzz.fuzz.partial_ratio_alignment` so the LLM never hallucinates offsets. Retry-with-chunked-fallback wraps the happy path for robustness against Gemini's occasional JSON truncation.

**Tech stack:** Python 3.12, pytest/pytest-asyncio, `openai` AsyncClient against Gemini's OpenAI-compat endpoint, `rapidfuzz` (new dep, ~500KB wheel).

**Hard constraints:**
- Preserve the `Entity` / `ExtractionResult` / `WikiArticle` dataclass shapes (downstream `pipeline.py` and `sources_map` consume them).
- Preserve `char_start`/`char_end` on entities — the UI uses them to render highlighted excerpts. Offsets must come from deterministic local alignment, not from the LLM.
- Don't touch the Phase 1 files from Phase 2's tasks or vice-versa — each phase must be reverifiable alone.

---

## File Structure

### Phase 1 — Template Wiki

| File | Change | Responsibility |
|---|---|---|
| `openraven/src/openraven/wiki/compiler.py` | Modify lines 120-159 | Rewrite `compile_wiki_for_graph` to call a new `_render_entity_from_graph` helper; keep `compile_article` untouched for future on-demand use |
| `openraven/src/openraven/wiki/compiler.py` | Add new function | `_render_entity_from_graph(name, graph, sources_map) -> WikiArticle` — pure synthesis from graph data, no I/O beyond graph reads |
| `openraven/tests/test_wiki_template.py` | Create | Unit tests for the template renderer and the rewired `compile_wiki_for_graph` |

### Phase 2 — Single-call Extraction

| File | Change | Responsibility |
|---|---|---|
| `openraven/pyproject.toml` | Modify dependencies | Add `rapidfuzz>=3.0` |
| `openraven/src/openraven/extraction/alignment.py` | Create | `align_span(haystack, needle) -> (start, end) | (None, None)` — exact-match first, rapidfuzz fallback |
| `openraven/src/openraven/extraction/extractor.py` | Modify lines 26-60 | Replace `_run_langextract` and `extract_entities` with `_extract_single_call` + `_extract_chunked_fallback`, plumb offsets through `align_span` |
| `openraven/tests/test_extraction_alignment.py` | Create | Unit tests for `align_span` — exact match, whitespace drift, Kangxi-radical drift, no match |
| `openraven/tests/test_extraction_single_call.py` | Create | Tests for the new `extract_entities` using a mocked `openai.AsyncOpenAI` (no real network) |

---

## Phase 1 — Template Wiki

### Task 1.1: Add `_render_entity_from_graph` helper (pure function)

**Files:**
- Modify: `openraven/src/openraven/wiki/compiler.py`
- Create: `openraven/tests/test_wiki_template.py`

- [ ] **Step 1: Write the failing unit test**

Create `openraven/tests/test_wiki_template.py`:

```python
from unittest.mock import MagicMock

from openraven.wiki.compiler import _render_entity_from_graph, WikiArticle


def _fake_subgraph(seed: str, neighbors: list[tuple[str, str]]) -> dict:
    """Build a fake get_subgraph() payload: seed + 1-hop neighbors as a name/type list."""
    return {
        "nodes": [
            {"id": seed, "labels": ["Concept"], "properties": {"entity_type": "Concept", "description": f"About {seed}"}, "is_seed": True},
            *[
                {"id": n, "labels": [t], "properties": {"entity_type": t}, "is_seed": False}
                for n, t in neighbors
            ],
        ],
        "edges": [{"id": f"{seed}-{n}", "type": "DIRECTED", "source": seed, "target": n, "properties": {}} for n, _ in neighbors],
    }


def test_render_entity_from_graph_basic():
    graph = MagicMock()
    graph.get_subgraph.return_value = _fake_subgraph("Kafka", [("Streaming", "Concept"), ("Confluent", "Organization")])
    sources_map = {"Kafka": [{"document": "arch.md", "excerpt": "Kafka is a distributed log", "char_start": 100, "char_end": 130}]}

    article = _render_entity_from_graph("Kafka", graph, sources_map)

    assert isinstance(article, WikiArticle)
    assert article.title == "Kafka"
    assert "Kafka" in article.summary
    assert {"Streaming", "Confluent"} == set(article.related_topics)
    assert article.sources[0]["document"] == "arch.md"
    assert article.confidence_score == 1.0   # template render = full confidence


def test_render_entity_from_graph_missing_node():
    """Entity not in graph yet (e.g. LangExtract found it but LightRAG hasn't inserted) → empty-but-valid article."""
    graph = MagicMock()
    graph.get_subgraph.return_value = {"nodes": [], "edges": []}

    article = _render_entity_from_graph("Ghost Entity", graph, {})

    assert article.title == "Ghost Entity"
    assert article.related_topics == []
    assert article.sources == []
    assert article.summary == "Ghost Entity"


def test_render_entity_from_graph_uses_node_description():
    """If the LightRAG node has a description attribute, use it as the summary."""
    graph = MagicMock()
    graph.get_subgraph.return_value = {
        "nodes": [{"id": "X", "labels": ["Concept"], "properties": {"description": "A specific concept about data ingestion."}, "is_seed": True}],
        "edges": [],
    }
    article = _render_entity_from_graph("X", graph, {})
    assert article.summary == "A specific concept about data ingestion."
```

- [ ] **Step 2: Run the test — expect failures**

```bash
cd /home/ubuntu/source/OpenRaven/openraven
.venv/bin/pytest tests/test_wiki_template.py -v
```

Expected: `ImportError: cannot import name '_render_entity_from_graph'`

- [ ] **Step 3: Implement `_render_entity_from_graph`**

Add this function to `openraven/src/openraven/wiki/compiler.py` directly above `compile_wiki_for_graph`:

```python
def _render_entity_from_graph(
    name: str,
    graph,
    sources_map: dict,
) -> WikiArticle:
    """Build a WikiArticle from graph data alone — no LLM calls.

    Pulls the entity's node + 1-hop neighbors via RavenGraph.get_subgraph,
    synthesizes a summary from the node's description attribute, and uses
    pre-collected source excerpts from sources_map.
    """
    subgraph = graph.get_subgraph(entities=[name], max_nodes=30)
    nodes = subgraph.get("nodes", [])

    seed = next((n for n in nodes if n.get("is_seed") or n.get("id") == name), None)
    description = ""
    entity_type = "Concept"
    if seed:
        props = seed.get("properties", {}) or {}
        description = props.get("description", "") or ""
        entity_type = props.get("entity_type") or (seed.get("labels", ["Concept"]) or ["Concept"])[0]

    related = [n["id"] for n in nodes if n.get("id") != name]

    sources = sources_map.get(name, [])

    summary = description if description else name
    sections = [
        {"heading": "Type", "content": entity_type},
    ]
    if sources:
        excerpts = "\n\n".join(f"> {s.get('excerpt', '').strip()}" for s in sources if s.get("excerpt"))
        if excerpts:
            sections.append({"heading": "Source Excerpts", "content": excerpts})

    return WikiArticle(
        title=name,
        summary=summary,
        sections=sections,
        sources=sources,
        related_topics=related,
        confidence_score=1.0,
    )
```

- [ ] **Step 4: Run the test — expect pass**

```bash
.venv/bin/pytest tests/test_wiki_template.py -v
```

Expected: `3 passed`

- [ ] **Step 5: Commit**

```bash
cd /home/ubuntu/source/OpenRaven
git add openraven/src/openraven/wiki/compiler.py openraven/tests/test_wiki_template.py
git commit -m "feat(wiki): add _render_entity_from_graph template helper

Pure synthesis from graph data + sources_map. No LLM. Groundwork for
replacing the eager per-entity article-generation in compile_wiki_for_graph."
```

---

### Task 1.2: Rewire `compile_wiki_for_graph` to use the template

**Files:**
- Modify: `openraven/src/openraven/wiki/compiler.py:120-159`
- Modify: `openraven/tests/test_wiki_template.py`

- [ ] **Step 1: Extend the test file with a compile-pipeline test**

Append to `openraven/tests/test_wiki_template.py`:

```python
import asyncio
from pathlib import Path


def test_compile_wiki_for_graph_writes_md_files_without_llm(tmp_path: Path):
    """compile_wiki_for_graph must write one .md per entity using only graph data (no LLM client)."""
    from openraven.wiki.compiler import compile_wiki_for_graph

    graph = MagicMock()
    graph.get_subgraph.side_effect = lambda entities, max_nodes: _fake_subgraph(
        entities[0],
        [("Related One", "Concept")] if entities[0] == "Alpha" else [],
    )
    sources_map = {"Alpha": [{"document": "doc.md", "excerpt": "Alpha excerpt", "char_start": 0, "char_end": 13}]}

    articles = asyncio.run(compile_wiki_for_graph(
        graph=graph,
        entities=["Alpha", "Beta"],
        sources_map=sources_map,
        api_key="unused",          # MUST be ignored by the new path
        output_dir=tmp_path,
    ))

    assert {a.title for a in articles} == {"Alpha", "Beta"}
    assert (tmp_path / "alpha.md").exists()
    assert (tmp_path / "beta.md").exists()
    alpha_md = (tmp_path / "alpha.md").read_text(encoding="utf-8")
    assert "Alpha" in alpha_md
    assert "Related One" in alpha_md
```

- [ ] **Step 2: Run test — expect failure (current compile_wiki_for_graph still calls the LLM)**

```bash
.venv/bin/pytest tests/test_wiki_template.py::test_compile_wiki_for_graph_writes_md_files_without_llm -v
```

Expected: failure — the current code calls `graph.query(...)` (which is unmocked async) and `compile_article(api_key=...)` which instantiates a real `openai.AsyncOpenAI`.

- [ ] **Step 3: Rewrite `compile_wiki_for_graph`**

Replace `compile_wiki_for_graph` in `openraven/src/openraven/wiki/compiler.py` (the entire function, currently lines 120-159) with:

```python
async def compile_wiki_for_graph(
    graph, entities: list[str], sources_map: dict, api_key: str,
    output_dir: Path, model: str = "claude-sonnet-4-6", max_concurrent: int = 5,
    on_progress: callable | None = None,
    base_url: str = "https://generativelanguage.googleapis.com/v1beta/openai/",
) -> list[WikiArticle]:
    """Render one wiki article per entity directly from the graph.

    No LLM is invoked; `api_key`, `model`, `base_url`, and `max_concurrent`
    are accepted for call-site compatibility but unused. Use
    `compile_article()` (still exported) for on-demand LLM prose via a
    future "Improve with AI" UI button.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    articles: list[WikiArticle] = []
    for i, name in enumerate(entities, start=1):
        article = _render_entity_from_graph(name, graph, sources_map)
        safe_name = name.replace("/", "_").replace(" ", "_").lower()
        (output_dir / f"{safe_name}.md").write_text(
            render_article_markdown(article), encoding="utf-8"
        )
        articles.append(article)
        if on_progress:
            on_progress(i, len(entities))

    return articles
```

- [ ] **Step 4: Run the test — expect pass**

```bash
.venv/bin/pytest tests/test_wiki_template.py -v
```

Expected: `4 passed`

- [ ] **Step 5: Run the existing `test_wiki.py` to confirm no regression**

```bash
.venv/bin/pytest tests/test_wiki.py -v
```

Expected: all existing tests still pass (they may rely on `compile_article`, which is untouched, or on `render_article_markdown`, also untouched).

- [ ] **Step 6: Commit**

```bash
git add openraven/src/openraven/wiki/compiler.py openraven/tests/test_wiki_template.py
git commit -m "feat(wiki): template-render wiki articles from graph instead of LLM

compile_wiki_for_graph now synthesizes each article from graph.get_subgraph()
+ sources_map with zero LLM calls, dropping Stage 3 latency from ~5min to
~seconds for 50 entities. Existing compile_article() remains for future
on-demand 'Improve with AI' UI path."
```

---

### Task 1.3: Integration check against live service

**Files:** none modified — live-service smoke test only.

- [ ] **Step 1: Restart core to load the new code**

```bash
pm2 restart openraven-core
sleep 8
curl -s -o /dev/null -w "health=%{http_code}\n" http://127.0.0.1:8741/health
```

Expected: `health=200`

- [ ] **Step 2: Drop any partial tenant state from prior aborted runs**

```bash
TENANT=/home/ubuntu/557b7be5-eeff-4bfe-a095-8a74c9addcab
/home/ubuntu/source/OpenRaven/openraven/.venv/bin/python -c "
import sqlite3
conn = sqlite3.connect('$TENANT/openraven.db')
n = conn.execute(\"DELETE FROM files WHERE status != 'graphed'\").rowcount
conn.commit()
print(f'deleted {n} non-graphed file record(s)')
"
rm -f $TENANT/lightrag_data/kv_store_*.json
```

- [ ] **Step 3: Trigger an ingest via the UI (openraven.cc/ingest) and time it**

Expected after Phase 1 only (LangExtract still chunked, graph insert tuned by Lever A):
- Stage 1 parse: ~3s
- Stage 2 extract + graph: ~80s
- Stage 3 wiki (template): **< 10s** ← the target of this phase
- Total: ~1.5 min

Verify in `~/.pm2/logs/openraven-core-out.log` that Stage 3 no longer shows Gemini calls from `compile_article`.

- [ ] **Step 4: No commit (smoke-test only)** — if output is correct, proceed to Phase 2.

---

## Phase 2 — Single-call Extraction

### Task 2.1: Add `rapidfuzz` dependency

**Files:**
- Modify: `openraven/pyproject.toml`

- [ ] **Step 1: Inspect current dependencies block**

```bash
grep -n "dependencies" /home/ubuntu/source/OpenRaven/openraven/pyproject.toml | head -5
```

Note the exact line numbers and style (quoted, comma-separated list).

- [ ] **Step 2: Add `rapidfuzz>=3.0` to the `dependencies = [...]` block**

Insert a new line inside the dependencies list, alphabetically near other `r*` packages. Example (line numbers vary by project):

```toml
    "rapidfuzz>=3.0",
```

- [ ] **Step 3: Install the new dep into the venv**

```bash
cd /home/ubuntu/source/OpenRaven/openraven
.venv/bin/pip install "rapidfuzz>=3.0"
.venv/bin/pip show rapidfuzz | head -3
```

Expected: `Name: rapidfuzz`, `Version: 3.x.y`.

- [ ] **Step 4: Verify pyproject is still consistent**

```bash
.venv/bin/pip check 2>&1 | head -5
```

Expected: `No broken requirements found.`

- [ ] **Step 5: Commit**

```bash
git add openraven/pyproject.toml
git commit -m "chore(deps): add rapidfuzz>=3.0 for single-call extractor offset alignment"
```

---

### Task 2.2: Offset-alignment helper (pure function)

**Files:**
- Create: `openraven/src/openraven/extraction/alignment.py`
- Create: `openraven/tests/test_extraction_alignment.py`

- [ ] **Step 1: Write the failing test**

Create `openraven/tests/test_extraction_alignment.py`:

```python
from openraven.extraction.alignment import align_span


def test_exact_match_returns_native_offsets():
    text = "Kafka is a distributed event streaming platform."
    start, end = align_span(text, "distributed event streaming")
    assert (start, end) == (11, 38)
    assert text[start:end] == "distributed event streaming"


def test_no_match_returns_none():
    start, end = align_span("some text", "completely unrelated string that is long enough to fail")
    assert (start, end) == (None, None)


def test_fuzzy_match_recovers_near_miss():
    # Simulate a tokenizer echoing a normalized form; the haystack has the raw original.
    # 'distributed log' is not a literal substring but partial_ratio finds the closest slice.
    text = "Kafka is a distributed event streaming platform for log pipelines."
    start, end = align_span(text, "distributed log")
    assert start is not None and end is not None
    assert 0 <= start < end <= len(text)


def test_cjk_exact_match():
    text = "BOXVERSE Intelligence Platform V3.3 — 產品功能總覽"
    start, end = align_span(text, "產品功能總覽")
    assert text[start:end] == "產品功能總覽"


def test_empty_needle_returns_none():
    start, end = align_span("anything", "")
    assert (start, end) == (None, None)
```

- [ ] **Step 2: Run — expect ImportError**

```bash
.venv/bin/pytest tests/test_extraction_alignment.py -v
```

Expected: `ModuleNotFoundError: No module named 'openraven.extraction.alignment'`.

- [ ] **Step 3: Implement `alignment.py`**

Create `openraven/src/openraven/extraction/alignment.py`:

```python
from __future__ import annotations

from rapidfuzz import fuzz


FUZZY_MIN_SCORE = 70.0


def align_span(haystack: str, needle: str) -> tuple[int | None, int | None]:
    """Return (start, end) char offsets of `needle` inside `haystack`.

    Exact substring match first. If not found, falls back to
    rapidfuzz.partial_ratio_alignment to recover from minor drift
    (whitespace, CJK normalization, small paraphrase). Returns
    (None, None) when neither approach produces a confident match.
    """
    if not needle:
        return (None, None)

    idx = haystack.find(needle)
    if idx >= 0:
        return (idx, idx + len(needle))

    align = fuzz.partial_ratio_alignment(needle, haystack)
    if align is None or align.score < FUZZY_MIN_SCORE:
        return (None, None)
    return (align.dest_start, align.dest_end)
```

- [ ] **Step 4: Run — expect pass**

```bash
.venv/bin/pytest tests/test_extraction_alignment.py -v
```

Expected: `5 passed`.

- [ ] **Step 5: Commit**

```bash
git add openraven/src/openraven/extraction/alignment.py openraven/tests/test_extraction_alignment.py
git commit -m "feat(extraction): add align_span helper for offset recovery

Exact substring match first, rapidfuzz.partial_ratio_alignment fallback
above FUZZY_MIN_SCORE=70. Groundwork for replacing LangExtract's internal
alignment with a deterministic local step so the LLM never hallucinates
char_start/char_end."
```

---

### Task 2.3: Single-call Gemini extractor

**Files:**
- Modify: `openraven/src/openraven/extraction/extractor.py`
- Create: `openraven/tests/test_extraction_single_call.py`

- [ ] **Step 1: Write the failing tests (mocked openai client)**

Create `openraven/tests/test_extraction_single_call.py`:

```python
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from openraven.extraction.extractor import Entity, ExtractionResult, extract_entities


SCHEMA = {
    "prompt_description": "Extract people, organizations, and concepts from the text.",
    "examples": [],
}


def _fake_gemini_response(entities: list[dict]) -> AsyncMock:
    resp = MagicMock()
    resp.choices = [MagicMock()]
    resp.choices[0].message.content = json.dumps({"entities": entities}, ensure_ascii=False)
    client = AsyncMock()
    client.chat.completions.create = AsyncMock(return_value=resp)
    return client


@pytest.mark.asyncio
async def test_extract_entities_single_call_returns_entities_with_offsets():
    text = "Alice works at Acme Corp on the distributed log project."
    client = _fake_gemini_response([
        {"extraction_text": "Alice",     "extraction_class": "Person",       "attributes": {}},
        {"extraction_text": "Acme Corp", "extraction_class": "Organization", "attributes": {}},
    ])

    with patch("openraven.extraction.extractor.openai.AsyncOpenAI", return_value=client):
        result = await extract_entities(
            text=text, source_document="doc.md", schema=SCHEMA, model_id="gemini-2.5-flash",
        )

    assert isinstance(result, ExtractionResult)
    names = [e.name for e in result.entities]
    assert names == ["Alice", "Acme Corp"]
    alice = result.entities[0]
    assert alice.char_start == text.index("Alice")
    assert alice.char_end == alice.char_start + len("Alice")
    assert alice.entity_type == "Person"
    assert alice.source_document == "doc.md"
    # ONE call, not chunked
    assert client.chat.completions.create.await_count == 1


@pytest.mark.asyncio
async def test_extract_entities_drops_hallucinated_spans():
    """LLM returns an entity whose text is not found in the source — it must be dropped."""
    text = "Alice works at Acme."
    client = _fake_gemini_response([
        {"extraction_text": "Alice",            "extraction_class": "Person", "attributes": {}},
        {"extraction_text": "Nonexistent Corp", "extraction_class": "Org",    "attributes": {}},
    ])
    with patch("openraven.extraction.extractor.openai.AsyncOpenAI", return_value=client):
        result = await extract_entities(text, "doc.md", SCHEMA, "gemini-2.5-flash")
    assert [e.name for e in result.entities] == ["Alice"]


@pytest.mark.asyncio
async def test_extract_entities_cjk_text():
    text = "台積電股價今日上漲, 本益比為25倍"
    client = _fake_gemini_response([
        {"extraction_text": "台積電",  "extraction_class": "上市公司",       "attributes": {}},
        {"extraction_text": "本益比", "extraction_class": "financial_metric", "attributes": {"value": "25"}},
    ])
    with patch("openraven.extraction.extractor.openai.AsyncOpenAI", return_value=client):
        result = await extract_entities(text, "zh.md", SCHEMA, "gemini-2.5-flash")
    assert [e.name for e in result.entities] == ["台積電", "本益比"]
    assert result.entities[0].attributes == {}
    assert result.entities[1].attributes == {"value": "25"}
```

- [ ] **Step 2: Run — expect failures (current extract_entities uses langextract, no mock hook for openai)**

```bash
.venv/bin/pytest tests/test_extraction_single_call.py -v
```

Expected: test failures — the current `_run_langextract` wraps `lx.extract`, not the openai client.

- [ ] **Step 3: Replace `_run_langextract` and rewire `extract_entities`**

In `openraven/src/openraven/extraction/extractor.py`, replace the entire file with:

```python
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field

import openai

from openraven.extraction.alignment import align_span


@dataclass
class Entity:
    name: str
    entity_type: str
    context: str
    source_document: str
    char_start: int | None = None
    char_end: int | None = None
    attributes: dict = field(default_factory=dict)


@dataclass
class ExtractionResult:
    entities: list[Entity]
    source_document: str


_SYSTEM = (
    "You are an information-extraction system. Return a JSON object with a single key "
    '"entities" whose value is an array of objects. Each object must have keys '
    '"extraction_text" (verbatim span copied character-for-character from the document), '
    '"extraction_class" (the entity type label), and optional "attributes" (object). '
    "Do not invent text that is not present. Do not return character offsets — only the "
    "verbatim span. Output JSON only, no prose."
)


def _build_prompt(schema: dict, text: str) -> str:
    parts = [schema.get("prompt_description", "")]
    examples = schema.get("examples") or []
    if examples:
        parts.append("\n\nExamples:\n" + json.dumps(examples, ensure_ascii=False, default=str))
    parts.append("\n\nDocument:\n" + text)
    return "".join(parts)


async def _extract_single_call(
    text: str, schema: dict, model_id: str, api_key: str, base_url: str,
) -> list[dict]:
    client = openai.AsyncOpenAI(api_key=api_key or "none", base_url=base_url)
    resp = await client.chat.completions.create(
        model=model_id,
        messages=[
            {"role": "system", "content": _SYSTEM},
            {"role": "user", "content": _build_prompt(schema, text)},
        ],
        response_format={"type": "json_object"},
    )
    raw = resp.choices[0].message.content or "{}"
    data = json.loads(raw)
    return data.get("entities", []) or []


async def extract_entities(
    text: str,
    source_document: str,
    schema: dict,
    model_id: str = "gemini-2.5-flash",
) -> ExtractionResult:
    api_key = os.environ.get("GEMINI_API_KEY", "") or os.environ.get("OPENAI_API_KEY", "")
    base_url = os.environ.get(
        "OPENRAVEN_LLM_BASE_URL",
        "https://generativelanguage.googleapis.com/v1beta/openai/",
    )
    raw_entities = await _extract_single_call(text, schema, model_id, api_key, base_url)

    entities: list[Entity] = []
    for item in raw_entities:
        span = (item.get("extraction_text") or "").strip()
        if not span:
            continue
        start, end = align_span(text, span)
        if start is None:
            continue                       # drop hallucinated / unalignable spans
        entities.append(Entity(
            name=span,
            entity_type=item.get("extraction_class") or "concept",
            context=span,
            source_document=source_document,
            char_start=start,
            char_end=end,
            attributes=item.get("attributes") if isinstance(item.get("attributes"), dict) else {},
        ))

    return ExtractionResult(entities=entities, source_document=source_document)


def enrich_text_for_rag(text: str, extraction_result: ExtractionResult) -> str:
    if not extraction_result.entities:
        return text

    entity_lines = []
    for e in extraction_result.entities:
        loc = ""
        if e.char_start is not None and e.char_end is not None:
            loc = f" [source:{e.source_document}:{e.char_start}-{e.char_end}]"
        entity_lines.append(f"[ENTITY:{e.entity_type}] {e.name}{loc}")

    header = "=== Extracted Entities ===\n" + "\n".join(entity_lines) + "\n=== End Entities ===\n\n"
    return header + text
```

- [ ] **Step 4: Run the new tests — expect pass**

```bash
.venv/bin/pytest tests/test_extraction_single_call.py -v
```

Expected: `3 passed`.

- [ ] **Step 5: Run the existing extraction test file for regression**

```bash
.venv/bin/pytest tests/test_extraction.py -v
```

Expected: all previously-passing tests pass. Any test that patched `openraven.extraction.extractor.lx` or `_run_langextract` will now fail — those must be updated in the next step if any exist. If zero failures, skip to Step 7.

- [ ] **Step 6 (if Step 5 had failures): Migrate old tests to the new mock shape**

Any pre-existing test that stubs `_run_langextract` or `langextract.extract` must now stub `openraven.extraction.extractor.openai.AsyncOpenAI`, following the `_fake_gemini_response` helper pattern from Task 2.3 Step 1. Update each failing test minimally — do not rewrite its assertions.

- [ ] **Step 7: Commit**

```bash
git add openraven/src/openraven/extraction/extractor.py openraven/tests/test_extraction_single_call.py
git commit -m "feat(extraction): single-call Gemini extractor with local offset alignment

Replaces the LangExtract chunked loop with one gemini-2.5-flash JSON call.
Char offsets are recovered locally via rapidfuzz.align_span — the LLM
never returns offsets (it cannot count CJK chars reliably). Spans that
don't align to the source are dropped, preventing hallucinated entities
from poisoning sources_map."
```

---

### Task 2.4: Retry + chunked fallback wrapper

**Files:**
- Modify: `openraven/src/openraven/extraction/extractor.py`
- Modify: `openraven/tests/test_extraction_single_call.py`

Gemini-2.5-flash has an intermittent bug where very-long JSON outputs repeat tokens until `max_output_tokens`, yielding invalid JSON. The robust shape: retry once; if it still fails, chunk the input and merge entities across chunks.

- [ ] **Step 1: Add failing tests for retry and chunked fallback**

Append to `openraven/tests/test_extraction_single_call.py`:

```python
@pytest.mark.asyncio
async def test_extract_retries_on_json_decode_error():
    """First Gemini response is invalid JSON, second is valid → final result succeeds."""
    bad_resp  = MagicMock(); bad_resp.choices  = [MagicMock()]; bad_resp.choices[0].message.content  = "not-json{{{"
    good_resp = MagicMock(); good_resp.choices = [MagicMock()]; good_resp.choices[0].message.content = json.dumps({"entities": [
        {"extraction_text": "Alice", "extraction_class": "Person", "attributes": {}},
    ]})
    client = AsyncMock()
    client.chat.completions.create = AsyncMock(side_effect=[bad_resp, good_resp])
    with patch("openraven.extraction.extractor.openai.AsyncOpenAI", return_value=client):
        result = await extract_entities("Alice works here.", "doc.md", SCHEMA, "gemini-2.5-flash")
    assert [e.name for e in result.entities] == ["Alice"]
    assert client.chat.completions.create.await_count == 2


@pytest.mark.asyncio
async def test_extract_chunks_on_repeated_failure():
    """Both attempts on the full doc fail → fall back to chunked extraction and merge."""
    bad = MagicMock(); bad.choices = [MagicMock()]; bad.choices[0].message.content = "not-json"
    chunk_ok_a = MagicMock(); chunk_ok_a.choices = [MagicMock()]; chunk_ok_a.choices[0].message.content = json.dumps({"entities": [
        {"extraction_text": "Alice", "extraction_class": "Person", "attributes": {}},
    ]})
    chunk_ok_b = MagicMock(); chunk_ok_b.choices = [MagicMock()]; chunk_ok_b.choices[0].message.content = json.dumps({"entities": [
        {"extraction_text": "Acme", "extraction_class": "Org", "attributes": {}},
    ]})
    client = AsyncMock()
    # sequence: full-doc attempt 1 fails, full-doc retry fails, then 2 chunk calls succeed
    client.chat.completions.create = AsyncMock(side_effect=[bad, bad, chunk_ok_a, chunk_ok_b])
    # Text sized to split into exactly 2 chunks at CHUNK_SIZE_CHARS=8000.
    # "Alice works here. "=18 chars * 300 = 5400. "Acme is a company. "=19 * 300 = 5700. Total 11100 → 2 chunks.
    text = ("Alice works here. " * 300) + ("Acme is a company. " * 300)
    with patch("openraven.extraction.extractor.openai.AsyncOpenAI", return_value=client):
        result = await extract_entities(text, "doc.md", SCHEMA, "gemini-2.5-flash")
    assert {e.name for e in result.entities} == {"Alice", "Acme"}
    assert client.chat.completions.create.await_count >= 3
```

- [ ] **Step 2: Run — expect failure (no retry or chunk logic yet)**

```bash
.venv/bin/pytest tests/test_extraction_single_call.py -v
```

Expected: the two new tests fail (`assert 2 == 1` or similar).

- [ ] **Step 3: Add retry + chunked fallback to `extractor.py`**

Replace the body of `extract_entities` and add two helpers. Edit `openraven/src/openraven/extraction/extractor.py`:

```python
CHUNK_SIZE_CHARS = 8000      # happy-path single-call preferred; only used on retry failure


async def _try_single_call(
    text: str, schema: dict, model_id: str, api_key: str, base_url: str,
) -> list[dict] | None:
    """Single call returning parsed entities, or None on JSONDecodeError / empty response."""
    try:
        return await _extract_single_call(text, schema, model_id, api_key, base_url)
    except (json.JSONDecodeError, ValueError):
        return None


def _chunk_text(text: str, size: int) -> list[str]:
    return [text[i:i + size] for i in range(0, len(text), size)] or [text]


async def extract_entities(
    text: str,
    source_document: str,
    schema: dict,
    model_id: str = "gemini-2.5-flash",
) -> ExtractionResult:
    api_key = os.environ.get("GEMINI_API_KEY", "") or os.environ.get("OPENAI_API_KEY", "")
    base_url = os.environ.get(
        "OPENRAVEN_LLM_BASE_URL",
        "https://generativelanguage.googleapis.com/v1beta/openai/",
    )

    raw_entities: list[dict] | None = None
    # Happy path: one call. Retry once on malformed JSON (known flash quirk).
    for _ in range(2):
        raw_entities = await _try_single_call(text, schema, model_id, api_key, base_url)
        if raw_entities is not None:
            break

    # Fallback: chunk and merge. Only kicks in on repeated JSON failure.
    if raw_entities is None:
        raw_entities = []
        seen = set()
        for chunk in _chunk_text(text, CHUNK_SIZE_CHARS):
            items = await _try_single_call(chunk, schema, model_id, api_key, base_url) or []
            for item in items:
                key = (item.get("extraction_text", ""), item.get("extraction_class", ""))
                if key in seen:
                    continue
                seen.add(key)
                raw_entities.append(item)

    entities: list[Entity] = []
    for item in raw_entities:
        span = (item.get("extraction_text") or "").strip()
        if not span:
            continue
        start, end = align_span(text, span)
        if start is None:
            continue
        entities.append(Entity(
            name=span,
            entity_type=item.get("extraction_class") or "concept",
            context=span,
            source_document=source_document,
            char_start=start,
            char_end=end,
            attributes=item.get("attributes") if isinstance(item.get("attributes"), dict) else {},
        ))

    return ExtractionResult(entities=entities, source_document=source_document)
```

- [ ] **Step 4: Run the retry/chunk tests — expect pass**

```bash
.venv/bin/pytest tests/test_extraction_single_call.py -v
```

Expected: `5 passed`.

- [ ] **Step 5: Run the full extraction-related suite**

```bash
.venv/bin/pytest tests/test_extraction.py tests/test_extraction_alignment.py tests/test_extraction_single_call.py -v
```

Expected: all green.

- [ ] **Step 6: Commit**

```bash
git add openraven/src/openraven/extraction/extractor.py openraven/tests/test_extraction_single_call.py
git commit -m "feat(extraction): retry + chunked fallback for Gemini JSON truncation

Flash-2.5 has a documented intermittent JSON-repetition bug on very long
outputs. Retry once on malformed JSON, then chunk the source at
CHUNK_SIZE_CHARS=8000 and merge entities by (text, class) key."
```

---

### Task 2.5: Integration check on the live service

**Files:** none.

- [ ] **Step 1: Restart core**

```bash
pm2 restart openraven-core
sleep 8
curl -s -o /dev/null -w "health=%{http_code}\n" http://127.0.0.1:8741/health
```

- [ ] **Step 2: Clean the test tenant's partial state (same block as Task 1.3 Step 2)**

```bash
TENANT=/home/ubuntu/557b7be5-eeff-4bfe-a095-8a74c9addcab
/home/ubuntu/source/OpenRaven/openraven/.venv/bin/python -c "
import sqlite3
conn = sqlite3.connect('$TENANT/openraven.db')
n = conn.execute(\"DELETE FROM files WHERE status != 'graphed'\").rowcount
conn.commit()
print(f'deleted {n}')
"
rm -f $TENANT/lightrag_data/kv_store_*.json
```

- [ ] **Step 3: Upload the test PDF through the UI and watch logs**

```bash
tail -n 0 -f ~/.pm2/logs/openraven-core-out.log ~/.pm2/logs/openraven-core-error.log 2>&1 \
  | grep --line-buffered -E 'POST /api/ingest|Extracting stage|Ingest job .* failed|articles_generated|Traceback|Exception'
```

Expected total wall time for the 8-page 77K-char zh-TW PDF:
- Stage 1 parse: ~3s
- Stage 2 extract (new): ~20–30s
- Stage 2 graph insert (Lever A): ~15–30s
- Stage 3 wiki (template): <5s
- **Total: ~45–70s** (vs. previous ~6.5 min baseline)

- [ ] **Step 4: Verify graph + wiki files exist for the tenant**

```bash
ls $TENANT/lightrag_data/graph_chunk_entity_relation.graphml
ls $TENANT/wiki/ | head
```

Both paths should contain data.

- [ ] **Step 5: No commit** — live-service smoke only. If anything regressed, revert Phase 2 with `git revert` and investigate before retrying.

---

## Phase-independent cleanup task (optional, do last)

### Task 3.1: Drop unused LangExtract dependency

Run only after Phase 2 is deployed and stable (≥1 successful production ingest).

**Files:**
- Modify: `openraven/pyproject.toml`

- [ ] **Step 1: Confirm no references remain**

```bash
grep -rn "langextract\|lx\.extract" /home/ubuntu/source/OpenRaven/openraven/src /home/ubuntu/source/OpenRaven/openraven/tests 2>&1 | grep -v "\.venv" | grep -v "\.pyc"
```

Expected: no results. If any file still imports `langextract`, STOP — the Phase 2 migration is incomplete.

- [ ] **Step 2: Remove the dep line from `pyproject.toml`**

Delete the `"langextract>=..."` entry from the `dependencies = [...]` block.

- [ ] **Step 3: Uninstall from venv**

```bash
cd /home/ubuntu/source/OpenRaven/openraven
.venv/bin/pip uninstall -y langextract
.venv/bin/pip check 2>&1 | head -3
```

Expected: `No broken requirements found.`

- [ ] **Step 4: Full suite regression**

```bash
.venv/bin/pytest tests/ -q
```

Expected: all passing tests still pass.

- [ ] **Step 5: Commit**

```bash
git add openraven/pyproject.toml
git commit -m "chore(deps): drop langextract (replaced by single-call extractor)"
```

---

## Success criteria (whole plan)

- [ ] `pytest tests/test_wiki_template.py tests/test_extraction_alignment.py tests/test_extraction_single_call.py` all green
- [ ] Existing `pytest tests/test_wiki.py tests/test_extraction.py tests/test_ingestion.py` still green
- [ ] Live-service ingest of the 8-page zh-TW PDF completes end-to-end in under 90 seconds
- [ ] Tenant's `lightrag_data/graph_chunk_entity_relation.graphml` and per-entity `wiki/*.md` files are written
- [ ] Zero Gemini calls logged during Stage 3 (wiki template is LLM-free)

## Rollback strategy

Phase 1 and Phase 2 each land as independent commits — either can be reverted individually with `git revert <sha>` and a PM2 restart without affecting the other.
