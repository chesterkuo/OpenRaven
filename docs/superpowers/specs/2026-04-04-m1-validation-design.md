# M1 Validation Suite — Design Spec

**Goal:** Achieve M1 acceptance criteria per PRD lines 721-722:
- QA accuracy >80%
- Source citation accuracy >95%

**Scope:** Add source citations to the query API, build a two-tier accuracy benchmark, and create a live KB smoke test.

---

## 1. API Enhancement — Source Citations in `/api/ask`

### Problem

`POST /api/ask` currently returns `{answer, mode}` — no source citations. We can't measure citation accuracy without them.

### Current flow

```
AskRequest(question, mode)
  → Pipeline.ask(question, mode)
    → RavenGraph.query(question, mode)
      → LightRAG.aquery(question, QueryParam(mode))
        → returns: str (answer text only)
```

LightRAG internally retrieves context chunks during RAG, but discards source metadata before returning the answer string.

### Proposed solution

**Approach: Extract sources from LightRAG's context, return alongside answer.**

LightRAG's `aquery` builds a context string from retrieved graph chunks before sending to the LLM. Each chunk originates from a document tracked by `file_path` in the GraphML. We intercept this context to extract source references.

#### Changes

**`openraven/src/openraven/graph/rag.py`** — Add `query_with_sources()`:

```python
@dataclass
class QueryResult:
    answer: str
    sources: list[dict]  # [{document, excerpt, char_start, char_end}]

async def query_with_sources(self, question: str, mode: QueryMode = "mix") -> QueryResult:
    """Query with source attribution."""
    await self.ensure_initialized()
    if not self._rag:
        return QueryResult(answer="", sources=[])

    # Use LightRAG's aquery — answer is a string
    answer = await self._rag.aquery(question, param=QueryParam(mode=mode))

    # Extract sources: search GraphML for entities mentioned in the answer
    sources = self._extract_sources_from_answer(answer)
    return QueryResult(answer=answer, sources=sources)
```

`_extract_sources_from_answer` scans the GraphML nodes, finds entities whose names or descriptions appear in the answer text, and returns their `file_path`, `description` (as excerpt), and stored char offsets. This leverages the entity metadata already stored by LangExtract during ingestion.

**`openraven/src/openraven/pipeline.py`** — Add `ask_with_sources()`:

```python
async def ask_with_sources(self, question: str, mode: str = "mix") -> QueryResult:
    return await self.graph.query_with_sources(question, mode=mode)
```

Keep existing `ask()` for backward compatibility.

**`openraven/src/openraven/api/server.py`** — Update response model:

```python
class SourceRef(BaseModel):
    document: str
    excerpt: str
    char_start: int = 0
    char_end: int = 0

class AskResponse(BaseModel):
    answer: str
    mode: str
    sources: list[SourceRef] = []
```

Update the endpoint:
```python
@app.post("/api/ask", response_model=AskResponse)
async def ask(req: AskRequest):
    result = await pipeline.ask_with_sources(req.question, mode=req.mode)
    return AskResponse(
        answer=result.answer,
        mode=req.mode,
        sources=[s for s in result.sources],
    )
```

**`openraven-ui/src/pages/AskPage.tsx`** — Display sources below the answer:

```tsx
{sources.length > 0 && (
  <div className="mt-4 border-t border-gray-800 pt-3">
    <h3 className="text-xs text-gray-500 uppercase mb-2">Sources ({sources.length})</h3>
    {sources.map((s, i) => (
      <div key={i} className="text-xs text-gray-400 mb-1">
        <span className="text-blue-400">{s.document}</span>
        {s.excerpt && <span className="ml-2 text-gray-500">— {s.excerpt}</span>}
      </div>
    ))}
  </div>
)}
```

#### Tests

Add to `openraven/tests/test_api.py`:

```python
def test_ask_response_includes_sources(client):
    """AskResponse model now has sources field."""
    response = client.post("/api/ask", json={"question": "test"})
    data = response.json()
    assert "sources" in data
    assert isinstance(data["sources"], list)
```

---

## 2. Benchmark Corpus

### Directory structure

```
openraven/tests/benchmark/
├── __init__.py
├── conftest.py           # Shared fixtures, LLM judge helper
├── corpus/               # 5-8 curated documents
│   ├── eng-adr-kafka.md
│   ├── eng-api-design.md
│   ├── eng-microservices.md
│   ├── fin-tsmc-report.md
│   ├── fin-q1-review.md
│   ├── gen-project-charter.md
│   ├── gen-meeting-notes.md
│   └── gen-onboarding-guide.md
├── ground_truth.json     # Q&A pairs with expected answers
├── test_accuracy.py      # Tier 1 + Tier 2 evaluation
└── test_smoke.py         # Live KB smoke test
```

### Ground truth format

```json
{
  "corpus_version": "1.0",
  "questions": [
    {
      "id": "eng-001",
      "question": "What messaging system does the architecture use?",
      "mode": "mix",
      "expected_facts": ["Kafka"],
      "expected_answer": "The architecture uses Apache Kafka as its messaging system for event-driven communication between microservices.",
      "source_documents": ["eng-adr-kafka.md"],
      "category": "factual_recall"
    },
    {
      "id": "eng-002",
      "question": "Why was event-driven architecture chosen over request-response?",
      "mode": "mix",
      "expected_facts": ["decoupling", "scalability"],
      "expected_answer": "Event-driven architecture was chosen for better decoupling between services and improved scalability under high load.",
      "source_documents": ["eng-adr-kafka.md", "eng-microservices.md"],
      "category": "reasoning"
    }
  ]
}
```

### Question categories

Target ~30 questions across these categories:

| Category | Count | Description |
|---|---|---|
| `factual_recall` | 10 | Single-fact lookup from one document |
| `reasoning` | 8 | Why/how questions requiring inference |
| `cross_document` | 6 | Requires synthesizing info from 2+ docs |
| `entity_specific` | 6 | Questions about specific extracted entities |

### Corpus documents

5-8 realistic documents covering:
- **Engineering** (3): Architecture Decision Records, API design docs, microservices overview
- **Finance** (2): Investment research reports, quarterly review
- **General** (2-3): Project charter, meeting notes, onboarding guide

Each document should be 500-2000 words — long enough for meaningful entity extraction, short enough for fast ingestion.

---

## 3. Two-Tier Evaluation

### Tier 1 — Fast (no LLM, CI-safe)

Runs as: `cd openraven && .venv/bin/python -m pytest tests/benchmark/test_accuracy.py -v -k tier1`

**Answer correctness:** Check that each `expected_facts` keyword appears in the answer (case-insensitive substring match).

```python
def evaluate_tier1(answer: str, expected_facts: list[str]) -> bool:
    answer_lower = answer.lower()
    return all(fact.lower() in answer_lower for fact in expected_facts)
```

**Citation correctness:** Check that at least one returned source document matches the `source_documents` list.

```python
def evaluate_citation_tier1(sources: list[dict], expected_docs: list[str]) -> bool:
    returned_docs = {s["document"] for s in sources}
    expected = set(expected_docs)
    return len(returned_docs & expected) > 0
```

**Pass criteria:**
- QA accuracy: >80% of questions have all expected facts in the answer
- Citation accuracy: >95% of questions cite at least one correct source document

### Tier 2 — Thorough (LLM-as-judge, on-demand)

Runs as: `cd openraven && .venv/bin/python -m pytest tests/benchmark/test_accuracy.py -v -k tier2`

Requires: `GEMINI_API_KEY` environment variable.

**Answer correctness:** Gemini grades each (question, expected_answer, actual_answer) triple:

```python
JUDGE_PROMPT = """Rate this answer on a 1-5 scale:
- 5: Fully correct, complete, no hallucination
- 4: Mostly correct, minor omissions
- 3: Partially correct, some inaccuracies
- 2: Mostly wrong or heavily hallucinated
- 1: Completely wrong or irrelevant

Question: {question}
Expected answer: {expected}
Actual answer: {actual}

Respond with JSON: {{"score": N, "reason": "brief explanation"}}"""
```

Score >=3 counts as correct. Target: >80% of questions score >=3.

**Citation quality:** For each returned source, verify the excerpt text actually appears in the cited document file (exact or fuzzy substring match within the char range).

```python
def verify_citation_quality(source: dict, corpus_dir: Path) -> bool:
    doc_path = corpus_dir / source["document"]
    if not doc_path.exists():
        return False
    content = doc_path.read_text()
    # Check excerpt appears in document
    return source["excerpt"].strip() in content
```

### Conftest setup

`conftest.py` handles:
- Fixture to ingest benchmark corpus into a temporary knowledge base (once per session)
- LLM judge helper function (Gemini via OpenAI-compat client, matching existing pattern)
- Skip Tier 2 tests if `GEMINI_API_KEY` not set
- `--llm-judge` pytest flag (optional, alternative to `-k tier2`)

```python
@pytest.fixture(scope="session")
def benchmark_kb(tmp_path_factory):
    """Ingest benchmark corpus into a fresh KB. Reused across all tests."""
    kb_dir = tmp_path_factory.mktemp("benchmark_kb")
    config = RavenConfig(working_dir=kb_dir)
    pipeline = Pipeline(config)
    # Ingest all corpus documents
    corpus_dir = Path(__file__).parent / "corpus"
    files = list(corpus_dir.glob("*.md"))
    asyncio.run(pipeline.add_files(files))
    return pipeline, config, corpus_dir
```

---

## 4. Live KB Smoke Test

`test_smoke.py` — runs against the user's actual knowledge base (not the benchmark corpus).

```python
def test_live_kb_smoke():
    """Quick check: query the live KB, verify non-empty responses."""
    # Uses default config (user's actual KB at ~/.openraven or configured path)
    # Queries 10 entity names from the graph as questions
    # Asserts: answer is non-empty, answer contains at least one entity name
```

Runs as: `cd openraven && .venv/bin/python -m pytest tests/benchmark/test_smoke.py -v`

This is a quick sanity check, not an accuracy measurement. It verifies the pipeline works end-to-end with real data.

---

## 5. Reporting

Both tiers output a structured report at the end of the test run:

```
═══════════════════════════════════════════
  M1 Validation Report
═══════════════════════════════════════════
  Corpus: 8 documents, 30 questions
  
  Tier 1 (keyword matching):
    QA Accuracy:      27/30 (90.0%) ✅ >80%
    Citation Accuracy: 29/30 (96.7%) ✅ >95%
  
  Tier 2 (LLM judge):
    QA Accuracy:      25/30 (83.3%) ✅ >80%
    Avg Score:        3.8/5.0
    Citation Quality:  28/30 (93.3%) ⚠️  <95%
  
  Live KB Smoke:      10/10 queries returned results ✅
═══════════════════════════════════════════
```

Report is printed to stdout AND saved to `openraven/tests/benchmark/report.txt`.

---

## File Summary

| File | Action | Responsibility |
|---|---|---|
| `openraven/src/openraven/graph/rag.py` | Modify | Add `QueryResult`, `query_with_sources()`, `_extract_sources_from_answer()` |
| `openraven/src/openraven/pipeline.py` | Modify | Add `ask_with_sources()` |
| `openraven/src/openraven/api/server.py` | Modify | Add `SourceRef` model, update `AskResponse`, update endpoint |
| `openraven-ui/src/pages/AskPage.tsx` | Modify | Display source citations below answer |
| `openraven/tests/test_api.py` | Modify | Test sources in AskResponse |
| `openraven/tests/benchmark/__init__.py` | Create | Package init |
| `openraven/tests/benchmark/conftest.py` | Create | Session-scoped KB fixture, LLM judge helper, pytest flags |
| `openraven/tests/benchmark/corpus/*.md` | Create | 5-8 benchmark documents |
| `openraven/tests/benchmark/ground_truth.json` | Create | ~30 Q&A pairs with expected facts + answers |
| `openraven/tests/benchmark/test_accuracy.py` | Create | Tier 1 + Tier 2 accuracy evaluation |
| `openraven/tests/benchmark/test_smoke.py` | Create | Live KB smoke test |

---

## Dependencies

- No new Python packages needed
- LLM judge uses existing OpenAI-compat client pattern (Gemini)
- Tier 1 tests run without any API key
- Tier 2 tests require `GEMINI_API_KEY`

## Acceptance

M1 is accepted when:
1. `pytest tests/benchmark/test_accuracy.py -k tier1` shows QA >80%, Citation >95%
2. `pytest tests/benchmark/test_accuracy.py -k tier2` shows QA >80%, Citation >95% (with Gemini)
3. `pytest tests/benchmark/test_smoke.py` passes on a real KB
4. `/api/ask` returns source citations in production
