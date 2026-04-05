# Stage 4: Knowledge Health Maintenance Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add periodic background health maintenance that detects staleness, finds knowledge gaps, discovers new connections between topics, and runs contradiction checks — the four PRD Stage 4 capabilities.

**Architecture:** A `HealthMaintainer` class runs the four analyses using the LightRAG graph and wiki articles. It's triggered two ways: (1) automatically after each ingestion completes, and (2) on-demand via `GET /api/health/run`. Results are stored as `HealthInsight` records in SQLite. A `GET /api/health/insights` endpoint exposes them to the UI. The discovery analyzer is rewritten to use the provider-aware OpenAI-compat client (replacing the dead Anthropic code).

**Tech Stack:** Python (FastAPI, SQLite, NetworkX, OpenAI-compat client), no new packages

**Key design decisions:**
- **No cron/scheduler** — runs after ingestion (the natural trigger) + on-demand. Avoids adding APScheduler/celery complexity.
- **LLM-powered gap + contradiction analysis** — uses the same provider config (Gemini/Ollama) as the rest of the pipeline.
- **Staleness is file-age based** — uses `updated_at` timestamp already in SQLite (currently unread).

---

## File Structure

| File | Action | Responsibility |
|---|---|---|
| `src/openraven/storage.py` | Modify | Expose `updated_at` in FileRecord + queries |
| `src/openraven/health/maintainer.py` | Create | Core health analysis: staleness, gaps, connections, contradictions |
| `src/openraven/health/reporter.py` | Modify | Fix `confidence_avg` wiring, add `stale_files` + `insight_count` |
| `src/openraven/discovery/analyzer.py` | Modify | Rewrite `discover_insights_with_llm` to use OpenAI-compat (Gemini/Ollama) |
| `src/openraven/pipeline.py` | Modify | Run health maintenance after ingestion |
| `src/openraven/api/server.py` | Modify | Add `/api/health/insights`, `/api/health/run` endpoints |
| `tests/test_storage.py` | Modify | Test `updated_at` field |
| `tests/test_health.py` | Modify | Test staleness detection, health maintainer |
| `tests/test_discovery.py` | Modify | Test rewritten analyzer |
| `tests/test_api.py` | Modify | Test new health endpoints |
| `openraven-ui/src/pages/StatusPage.tsx` | Modify | Show health insights |

---

## Task 1: Storage — expose `updated_at` in FileRecord

**Files:**
- Modify: `openraven/src/openraven/storage.py`
- Modify: `openraven/tests/test_storage.py`

- [ ] **Step 1: Write failing test**

Add to `openraven/tests/test_storage.py`:

```python
def test_file_record_has_updated_at(tmp_path) -> None:
    store = MetadataStore(tmp_path / "test.db")
    store.upsert_file(FileRecord(path="/doc.md", hash="abc", format="markdown", char_count=100, status="ingested"))
    record = store.get_file("/doc.md")
    assert record is not None
    assert record.updated_at is not None
    assert isinstance(record.updated_at, str)
    store.close()


def test_list_stale_files(tmp_path) -> None:
    store = MetadataStore(tmp_path / "test.db")
    store.upsert_file(FileRecord(path="/old.md", hash="a", format="markdown", char_count=50, status="graphed"))
    # Force the timestamp to 60 days ago
    store._conn.execute("UPDATE files SET updated_at = datetime('now', '-60 days') WHERE path = '/old.md'")
    store._conn.commit()
    store.upsert_file(FileRecord(path="/new.md", hash="b", format="markdown", char_count=50, status="graphed"))

    stale = store.list_stale_files(days=30)
    assert len(stale) == 1
    assert stale[0].path == "/old.md"
    store.close()
```

- [ ] **Step 2: Run to verify failure**

Run: `cd openraven && .venv/bin/python -m pytest tests/test_storage.py -v -k "updated_at or stale"`

- [ ] **Step 3: Implement**

Update `openraven/src/openraven/storage.py`:

Add `updated_at` to `FileRecord`:

```python
@dataclass
class FileRecord:
    """Metadata record for an ingested file."""
    path: str
    hash: str
    format: str
    char_count: int
    status: str
    updated_at: str | None = None
```

Update `get_file` to read `updated_at`:

```python
def get_file(self, path: str) -> FileRecord | None:
    row = self._conn.execute("SELECT * FROM files WHERE path = ?", (path,)).fetchone()
    if row is None:
        return None
    return FileRecord(
        path=row["path"], hash=row["hash"], format=row["format"],
        char_count=row["char_count"], status=row["status"],
        updated_at=row["updated_at"],
    )
```

Update `list_files` similarly to include `updated_at`.

Add `list_stale_files`:

```python
def list_stale_files(self, days: int = 30) -> list[FileRecord]:
    rows = self._conn.execute(
        "SELECT * FROM files WHERE updated_at < datetime('now', ?)",
        (f"-{days} days",),
    ).fetchall()
    return [
        FileRecord(path=r["path"], hash=r["hash"], format=r["format"],
                   char_count=r["char_count"], status=r["status"],
                   updated_at=r["updated_at"])
        for r in rows
    ]
```

- [ ] **Step 4: Run tests**

Run: `cd openraven && .venv/bin/python -m pytest tests/test_storage.py -v`

- [ ] **Step 5: Commit**

```bash
git add openraven/src/openraven/storage.py openraven/tests/test_storage.py
git commit -m "feat(storage): expose updated_at in FileRecord, add list_stale_files"
```

---

## Task 2: Health maintainer — staleness + gap + connection analysis

**Files:**
- Create: `openraven/src/openraven/health/maintainer.py`
- Modify: `openraven/tests/test_health.py`

- [ ] **Step 1: Write failing tests**

Add to `openraven/tests/test_health.py`:

```python
from openraven.health.maintainer import HealthMaintainer, HealthInsight


def test_detect_stale_files(tmp_path) -> None:
    from openraven.storage import MetadataStore, FileRecord
    store = MetadataStore(tmp_path / "test.db")
    store.upsert_file(FileRecord(path="/old.md", hash="a", format="markdown", char_count=50, status="graphed"))
    store._conn.execute("UPDATE files SET updated_at = datetime('now', '-60 days') WHERE path = '/old.md'")
    store._conn.commit()

    maintainer = HealthMaintainer(store=store, graph=None, config=None)
    insights = maintainer.detect_staleness(days=30)
    assert len(insights) == 1
    assert insights[0].insight_type == "stale"
    assert "/old.md" in insights[0].description
    store.close()


def test_no_stale_files(tmp_path) -> None:
    from openraven.storage import MetadataStore, FileRecord
    store = MetadataStore(tmp_path / "test.db")
    store.upsert_file(FileRecord(path="/new.md", hash="a", format="markdown", char_count=50, status="graphed"))

    maintainer = HealthMaintainer(store=store, graph=None, config=None)
    insights = maintainer.detect_staleness(days=30)
    assert len(insights) == 0
    store.close()


def test_detect_new_connections(tmp_path) -> None:
    import networkx as nx
    from openraven.graph.rag import RavenGraph

    graph = RavenGraph.create_lazy(working_dir=tmp_path / "lightrag_data")
    g = nx.Graph()
    # Create two clusters connected by a single bridge node
    g.add_node("A", entity_type="concept", description="Concept A")
    g.add_node("B", entity_type="concept", description="Concept B")
    g.add_node("BRIDGE", entity_type="concept", description="Bridge concept")
    g.add_node("C", entity_type="concept", description="Concept C")
    g.add_node("D", entity_type="concept", description="Concept D")
    g.add_edge("A", "B", weight="1.0")
    g.add_edge("A", "BRIDGE", weight="1.0")
    g.add_edge("BRIDGE", "C", weight="1.0")
    g.add_edge("C", "D", weight="1.0")
    graph_file = graph.working_dir / "graph_chunk_entity_relation.graphml"
    nx.write_graphml(g, str(graph_file))

    maintainer = HealthMaintainer(store=None, graph=graph, config=None)
    insights = maintainer.detect_bridge_connections()
    assert len(insights) >= 1
    assert any("BRIDGE" in i.description for i in insights)


def test_health_insight_structure() -> None:
    insight = HealthInsight(
        insight_type="stale", title="Stale files", description="2 files not updated in 30+ days",
        related_entities=["/old.md"], severity="warning",
    )
    assert insight.insight_type == "stale"
    assert insight.severity == "warning"
```

- [ ] **Step 2: Run to verify failure**

Run: `cd openraven && .venv/bin/python -m pytest tests/test_health.py -v -k "stale or connection or health_insight"`

- [ ] **Step 3: Create `health/maintainer.py`**

Create `openraven/src/openraven/health/maintainer.py`:

```python
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class HealthInsight:
    insight_type: str  # "stale", "gap", "connection", "contradiction"
    title: str
    description: str
    related_entities: list[str] = field(default_factory=list)
    severity: str = "info"  # "info", "warning", "critical"


class HealthMaintainer:
    """Runs Stage 4 health analyses on the knowledge base."""

    def __init__(self, store, graph, config) -> None:
        self.store = store
        self.graph = graph
        self.config = config

    def detect_staleness(self, days: int = 30) -> list[HealthInsight]:
        """Find files not updated in the given number of days."""
        if not self.store:
            return []
        stale = self.store.list_stale_files(days=days)
        if not stale:
            return []
        paths = [f.path for f in stale]
        return [HealthInsight(
            insight_type="stale",
            title=f"{len(stale)} stale file{'s' if len(stale) != 1 else ''}",
            description=f"Files not updated in {days}+ days: {', '.join(Path(p).name for p in paths[:5])}",
            related_entities=paths[:10],
            severity="warning",
        )]

    def detect_bridge_connections(self) -> list[HealthInsight]:
        """Find nodes that bridge otherwise disconnected clusters (high betweenness centrality)."""
        if not self.graph:
            return []
        import networkx as nx

        graph_file = self.graph.working_dir / "graph_chunk_entity_relation.graphml"
        if not graph_file.exists():
            return []
        try:
            g = nx.read_graphml(str(graph_file))
        except Exception:
            return []

        if g.number_of_nodes() < 5:
            return []

        betweenness = nx.betweenness_centrality(g)
        # Find nodes with betweenness significantly above average
        avg_bc = sum(betweenness.values()) / len(betweenness)
        bridges = [(node, bc) for node, bc in betweenness.items() if bc > avg_bc * 2 and bc > 0.1]
        bridges.sort(key=lambda x: x[1], reverse=True)

        insights = []
        for node, bc in bridges[:5]:
            neighbors = list(g.neighbors(node))
            insights.append(HealthInsight(
                insight_type="connection",
                title=f"Bridge concept: {node}",
                description=f"{node} connects {len(neighbors)} topics (centrality: {bc:.2f}). "
                            f"Connected to: {', '.join(neighbors[:5])}",
                related_entities=[node] + neighbors[:5],
                severity="info",
            ))
        return insights

    def detect_knowledge_gaps(self) -> list[HealthInsight]:
        """Find isolated nodes or small disconnected components (potential knowledge gaps)."""
        if not self.graph:
            return []
        import networkx as nx

        graph_file = self.graph.working_dir / "graph_chunk_entity_relation.graphml"
        if not graph_file.exists():
            return []
        try:
            g = nx.read_graphml(str(graph_file))
        except Exception:
            return []

        if g.number_of_nodes() < 3:
            return []

        # Find isolated nodes (degree 0 or 1)
        isolated = [n for n, d in g.degree() if d <= 1]
        insights = []
        if isolated:
            insights.append(HealthInsight(
                insight_type="gap",
                title=f"{len(isolated)} weakly connected concept{'s' if len(isolated) != 1 else ''}",
                description=f"These concepts have few connections and may need more context: "
                            f"{', '.join(isolated[:5])}",
                related_entities=isolated[:10],
                severity="info" if len(isolated) < 5 else "warning",
            ))

        # Find small disconnected components
        components = list(nx.connected_components(g))
        if len(components) > 1:
            small = [c for c in components if len(c) < 3]
            if small:
                names = [next(iter(c)) for c in small[:5]]
                insights.append(HealthInsight(
                    insight_type="gap",
                    title=f"{len(small)} disconnected knowledge cluster{'s' if len(small) != 1 else ''}",
                    description=f"Small isolated clusters found: {', '.join(names)}. "
                                f"Adding more related documents may help connect them.",
                    related_entities=names,
                    severity="warning",
                ))

        return insights

    def run_all(self, staleness_days: int = 30) -> list[HealthInsight]:
        """Run all health analyses and return combined insights."""
        insights = []
        insights.extend(self.detect_staleness(staleness_days))
        insights.extend(self.detect_bridge_connections())
        insights.extend(self.detect_knowledge_gaps())
        return insights
```

- [ ] **Step 4: Run tests**

Run: `cd openraven && .venv/bin/python -m pytest tests/test_health.py -v`

- [ ] **Step 5: Run all tests**

Run: `cd openraven && .venv/bin/python -m pytest tests/ -v --ignore=tests/test_integration.py`

- [ ] **Step 6: Commit**

```bash
git add openraven/src/openraven/health/maintainer.py openraven/tests/test_health.py
git commit -m "feat(health): add HealthMaintainer with staleness, gaps, and bridge detection"
```

---

## Task 3: Fix discovery analyzer — replace Anthropic with OpenAI-compat

**Files:**
- Modify: `openraven/src/openraven/discovery/analyzer.py`
- Modify: `openraven/tests/test_discovery.py`

- [ ] **Step 1: Write failing test**

Add to `openraven/tests/test_discovery.py`:

```python
def test_discover_insights_with_llm_signature() -> None:
    import inspect
    from openraven.discovery.analyzer import discover_insights_with_llm
    sig = inspect.signature(discover_insights_with_llm)
    assert "base_url" in sig.parameters
    assert "api_key" in sig.parameters
    # Should NOT import anthropic anymore
    import openraven.discovery.analyzer as mod
    source = inspect.getsource(mod)
    assert "anthropic" not in source.lower() or "anthropic" in source.lower().split("openai")[0] == False
```

Actually, let's write a more concrete test:

```python
def test_analyzer_does_not_import_anthropic() -> None:
    """The old analyzer used anthropic client which was never configured. Verify it's gone."""
    import inspect
    import openraven.discovery.analyzer as mod
    source = inspect.getsource(mod)
    assert "import anthropic" not in source
```

- [ ] **Step 2: Run to verify failure**

Run: `cd openraven && .venv/bin/python -m pytest tests/test_discovery.py -v -k "anthropic"`
Expected: FAIL (source still contains `import anthropic`)

- [ ] **Step 3: Rewrite analyzer.py**

Replace `openraven/src/openraven/discovery/analyzer.py`:

```python
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field

import openai

logger = logging.getLogger(__name__)

_DISCOVER_PROMPT_TMPL = (
    "Based on this knowledge base overview, generate 3-5 proactive discovery insights.\n\n"
    "Overview:\n{overview}\n\n"
    'Return JSON array:\n[\n  {{\n'
    '    "insight_type": "theme|cluster|gap|trend",\n'
    '    "title": "short title",\n'
    '    "description": "1-2 sentence description of what was found",\n'
    '    "related_entities": ["entity1", "entity2"]\n'
    "  }}\n]"
)


@dataclass
class DiscoveryInsight:
    insight_type: str  # "theme", "cluster", "gap", "trend"
    title: str
    description: str
    related_entities: list[str] = field(default_factory=list)
    document_count: int = 0


def analyze_themes(graph_stats: dict) -> list[DiscoveryInsight]:
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

    if len(topics) >= 3:
        insights.append(DiscoveryInsight(
            insight_type="cluster",
            title="Top Knowledge Areas",
            description=f"Found {len(topics)} distinct topics in your knowledge base.",
            related_entities=topics[:10],
            document_count=len(topics),
        ))

    return insights


async def discover_insights_with_llm(
    graph, api_key: str, model: str = "gemini-2.5-flash",
    base_url: str = "https://generativelanguage.googleapis.com/v1beta/openai/",
) -> list[DiscoveryInsight]:
    """Generate discovery insights using LLM analysis of the knowledge graph."""
    overview = await graph.query(
        "What are the main themes, recurring patterns, and frameworks in this knowledge base? "
        "Identify clusters of related topics and any notable connections between different areas.",
        mode="global",
    )

    if not overview or not overview.strip():
        return []

    prompt = _DISCOVER_PROMPT_TMPL.format(overview=overview)

    client = openai.AsyncOpenAI(api_key=api_key or "ollama", base_url=base_url)
    response = await client.chat.completions.create(
        model=model, max_tokens=1500,
        messages=[{"role": "user", "content": prompt}],
    )

    content = response.choices[0].message.content
    if "```json" in content:
        content = content.split("```json")[1].split("```")[0]
    elif "```" in content:
        content = content.split("```")[1].split("```")[0]

    raw_insights = json.loads(content.strip())

    return [
        DiscoveryInsight(
            insight_type=item["insight_type"], title=item["title"],
            description=item["description"],
            related_entities=item.get("related_entities", []),
        )
        for item in raw_insights
    ]
```

- [ ] **Step 4: Run tests**

Run: `cd openraven && .venv/bin/python -m pytest tests/test_discovery.py -v`

- [ ] **Step 5: Commit**

```bash
git add openraven/src/openraven/discovery/analyzer.py openraven/tests/test_discovery.py
git commit -m "fix(discovery): replace dead Anthropic client with OpenAI-compat (Gemini/Ollama)"
```

---

## Task 4: Wire health maintenance into pipeline + API

**Files:**
- Modify: `openraven/src/openraven/pipeline.py`
- Modify: `openraven/src/openraven/api/server.py`
- Modify: `openraven/tests/test_api.py`

- [ ] **Step 1: Write failing tests**

Add to `openraven/tests/test_api.py`:

```python
def test_health_insights_endpoint(client: TestClient) -> None:
    response = client.get("/api/health/insights")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


def test_health_run_endpoint(client: TestClient) -> None:
    response = client.post("/api/health/run")
    assert response.status_code == 200
    data = response.json()
    assert "insights_count" in data
```

- [ ] **Step 2: Add health endpoints to server.py**

Add inside `create_app()`:

```python
@app.get("/api/health/insights")
async def health_insights():
    from openraven.health.maintainer import HealthMaintainer
    maintainer = HealthMaintainer(store=pipeline.store, graph=pipeline.graph, config=config)
    insights = maintainer.run_all()
    return [
        {
            "insight_type": i.insight_type,
            "title": i.title,
            "description": i.description,
            "related_entities": i.related_entities,
            "severity": i.severity,
        }
        for i in insights
    ]

@app.post("/api/health/run")
async def health_run():
    from openraven.health.maintainer import HealthMaintainer
    maintainer = HealthMaintainer(store=pipeline.store, graph=pipeline.graph, config=config)
    insights = maintainer.run_all()
    return {"insights_count": len(insights), "insights": [
        {"insight_type": i.insight_type, "title": i.title, "severity": i.severity}
        for i in insights
    ]}
```

- [ ] **Step 3: Run tests**

Run: `cd openraven && .venv/bin/python -m pytest tests/test_api.py -v -k "health"`

- [ ] **Step 4: Run all tests**

Run: `cd openraven && .venv/bin/python -m pytest tests/ -v --ignore=tests/test_integration.py`

- [ ] **Step 5: Commit**

```bash
git add openraven/src/openraven/api/server.py openraven/tests/test_api.py
git commit -m "feat(api): add health insights and maintenance run endpoints"
```

---

## Task 5: StatusPage — show health insights

**Files:**
- Modify: `openraven-ui/src/pages/StatusPage.tsx`

- [ ] **Step 1: Update StatusPage to fetch and display health insights**

Read the current `openraven-ui/src/pages/StatusPage.tsx` first.

Add a third state + useEffect for health insights, after the existing provider fetch:

```tsx
const [insights, setInsights] = useState<{insight_type: string; title: string; description: string; severity: string}[]>([]);
useEffect(() => { fetch("/api/health/insights").then(r => r.json()).then(setInsights).catch(() => {}); }, []);
```

Add a health insights section after the top topics, before the closing `</div>`:

```tsx
{insights.length > 0 && (
  <div className="mt-6">
    <h2 className="text-lg font-semibold mb-3">Health Insights</h2>
    <div className="flex flex-col gap-2">
      {insights.map((insight, i) => (
        <div key={i} className={`border rounded-lg p-3 text-sm ${
          insight.severity === "warning" ? "border-amber-700 bg-amber-950/30" :
          insight.severity === "critical" ? "border-red-700 bg-red-950/30" :
          "border-gray-700 bg-gray-900"
        }`}>
          <div className="flex items-center gap-2 mb-1">
            <span className={`text-xs font-medium uppercase ${
              insight.severity === "warning" ? "text-amber-400" :
              insight.severity === "critical" ? "text-red-400" :
              "text-blue-400"
            }`}>{insight.insight_type}</span>
            <span className="text-gray-200 font-medium">{insight.title}</span>
          </div>
          <p className="text-gray-400">{insight.description}</p>
        </div>
      ))}
    </div>
  </div>
)}
```

- [ ] **Step 2: Build**

Run: `cd openraven-ui && bun run build`

- [ ] **Step 3: Commit**

```bash
git add openraven-ui/src/pages/StatusPage.tsx
git commit -m "feat(ui): show health insights on status page"
```

---

## Task 6: E2E verification

- [ ] **Step 1: Run full test suite**

```bash
cd openraven && .venv/bin/python -m pytest tests/ -v --ignore=tests/test_integration.py
cd openraven-ui && bun test tests/ && bun run build
```

- [ ] **Step 2: Restart PM2 and verify endpoints**

```bash
pm2 restart all && sleep 10
curl -sf http://localhost:8741/api/health/insights | python3 -m json.tool
curl -sf -X POST http://localhost:8741/api/health/run | python3 -m json.tool
```

- [ ] **Step 3: Commit if fixes needed**

---

## Summary

| Task | What | Tests Added |
|---|---|---|
| 1 | Storage: expose `updated_at`, add `list_stale_files` | 2 storage tests |
| 2 | HealthMaintainer: staleness + gaps + bridges | 4 health tests |
| 3 | Fix analyzer: Anthropic → OpenAI-compat | 1 discovery test |
| 4 | API: health insights + run endpoints | 2 API tests |
| 5 | StatusPage: show health insights | Build check |
| 6 | E2E verification | Full suite |

**Total new tests: 9**

**PRD Stage 4 coverage:**
- Staleness marking → `detect_staleness()` — checks `updated_at` age
- Knowledge gap analysis → `detect_knowledge_gaps()` — finds isolated nodes + disconnected clusters
- New connection discovery → `detect_bridge_connections()` — betweenness centrality for bridge nodes
- Contradiction detection → Deferred to LLM-powered analysis (requires comparing wiki article claims against source documents — complex, better as a follow-up)
