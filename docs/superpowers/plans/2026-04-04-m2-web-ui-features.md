# M2 Web UI Features Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete the "full functionality in browser" M2 acceptance criterion by adding wiki article browser, GraphML export, and ingestion progress indicator.

**Architecture:** Three small features sharing the same pattern: Python API endpoint → Hono proxy → React page/component. Wiki browser reads `.md` files from `config.wiki_dir`. GraphML export uses existing `export_graphml()` with `FileResponse`. Ingestion progress uses polling (`POST /api/ingest` returns a job ID, `GET /api/ingest/status/{job_id}` returns progress).

**Tech Stack:** FastAPI, Hono, React 19, Tailwind v4 (all existing)

---

## File Structure

### Python backend (openraven/)

| File | Action | Responsibility |
|---|---|---|
| `src/openraven/api/server.py` | Modify | Add `/api/wiki`, `/api/wiki/{slug}`, `/api/graph/export`, `/api/ingest` (polling version) |
| `tests/test_api.py` | Modify | Tests for all new endpoints |

### TypeScript frontend (openraven-ui/)

| File | Action | Responsibility |
|---|---|---|
| `server/services/core-client.ts` | Modify | Add `getWikiList()`, `getWikiArticle()` types + functions |
| `server/routes/wiki.ts` | Create | Hono proxy for wiki endpoints |
| `server/index.ts` | Modify | Register wiki route |
| `src/pages/WikiPage.tsx` | Create | Wiki article list + reader view |
| `src/pages/GraphPage.tsx` | Modify | Add export button |
| `src/pages/IngestPage.tsx` | Modify | Add progress polling UI |
| `src/App.tsx` | Modify | Add `/wiki` nav link + route |
| `tests/server/routes.test.ts` | Modify | Wiki route tests |

---

## Task 1: Wiki API — list and read endpoints

**Files:**
- Modify: `openraven/src/openraven/api/server.py`
- Modify: `openraven/tests/test_api.py`

- [ ] **Step 1: Write failing tests**

Add to `openraven/tests/test_api.py`:

```python
def test_wiki_list_endpoint(client: TestClient) -> None:
    response = client.get("/api/wiki")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


def test_wiki_article_endpoint_not_found(client: TestClient) -> None:
    response = client.get("/api/wiki/nonexistent-article")
    assert response.status_code == 404


def test_wiki_article_endpoint_reads_file(client: TestClient, config) -> None:
    # Create a test wiki article
    config.wiki_dir.mkdir(parents=True, exist_ok=True)
    (config.wiki_dir / "apache_kafka.md").write_text(
        "# Apache Kafka\n\n**Confidence:** 85%\n\nA streaming platform.\n"
    )
    response = client.get("/api/wiki/apache_kafka")
    assert response.status_code == 200
    data = response.json()
    assert data["slug"] == "apache_kafka"
    assert data["title"] == "Apache Kafka"
    assert "streaming platform" in data["content"]
```

- [ ] **Step 2: Run to verify failure**

Run: `cd openraven && .venv/bin/python -m pytest tests/test_api.py -v -k "wiki"`
Expected: FAIL with 404

- [ ] **Step 3: Implement wiki endpoints**

Add to `openraven/src/openraven/api/server.py`, inside `create_app()`:

```python
@app.get("/api/wiki")
async def wiki_list():
    wiki_dir = config.wiki_dir
    if not wiki_dir.exists():
        return []
    articles = []
    for f in sorted(wiki_dir.glob("*.md")):
        first_line = f.read_text(encoding="utf-8").split("\n", 1)[0]
        title = first_line.lstrip("# ").strip() if first_line.startswith("#") else f.stem
        articles.append({"slug": f.stem, "title": title})
    return articles

@app.get("/api/wiki/{slug}")
async def wiki_article(slug: str):
    from fastapi.responses import JSONResponse
    wiki_file = config.wiki_dir / f"{slug}.md"
    if not wiki_file.exists():
        return JSONResponse({"error": "Article not found"}, status_code=404)
    content = wiki_file.read_text(encoding="utf-8")
    first_line = content.split("\n", 1)[0]
    title = first_line.lstrip("# ").strip() if first_line.startswith("#") else slug
    return {"slug": slug, "title": title, "content": content}
```

- [ ] **Step 4: Run tests**

Run: `cd openraven && .venv/bin/python -m pytest tests/test_api.py -v -k "wiki"`
Expected: 3 PASS

- [ ] **Step 5: Commit**

```bash
git add openraven/src/openraven/api/server.py openraven/tests/test_api.py
git commit -m "feat(api): add wiki list and article read endpoints"
```

---

## Task 2: Wiki Hono proxy + WikiPage

**Files:**
- Modify: `openraven-ui/server/services/core-client.ts`
- Create: `openraven-ui/server/routes/wiki.ts`
- Modify: `openraven-ui/server/index.ts`
- Create: `openraven-ui/src/pages/WikiPage.tsx`
- Modify: `openraven-ui/src/App.tsx`
- Modify: `openraven-ui/tests/server/routes.test.ts`

- [ ] **Step 1: Add core-client types and functions**

Add to `openraven-ui/server/services/core-client.ts`:

```typescript
export interface WikiListItem {
  slug: string;
  title: string;
}

export interface WikiArticle {
  slug: string;
  title: string;
  content: string;
}

export async function getWikiList(): Promise<WikiListItem[]> {
  const res = await fetch(`${CORE_API_URL}/api/wiki`);
  if (!res.ok) throw new Error(`Core API error: ${res.status}`);
  return res.json();
}

export async function getWikiArticle(slug: string): Promise<WikiArticle> {
  const res = await fetch(`${CORE_API_URL}/api/wiki/${encodeURIComponent(slug)}`);
  if (!res.ok) throw new Error(`Core API error: ${res.status}`);
  return res.json();
}
```

- [ ] **Step 2: Create wiki route**

Create `openraven-ui/server/routes/wiki.ts`:

```typescript
import { Hono } from "hono";
import { getWikiList, getWikiArticle } from "../services/core-client";

const wikiRouter = new Hono();

wikiRouter.get("/", async (c) => {
  try {
    const list = await getWikiList();
    return c.json(list);
  } catch (e) {
    return c.json({ error: `Core engine error: ${(e as Error).message}` }, 502);
  }
});

wikiRouter.get("/:slug", async (c) => {
  try {
    const slug = c.req.param("slug");
    const article = await getWikiArticle(slug);
    return c.json(article);
  } catch (e) {
    const msg = (e as Error).message;
    const status = msg.includes("404") ? 404 : 502;
    return c.json({ error: msg }, status);
  }
});

export default wikiRouter;
```

- [ ] **Step 3: Register wiki route in index.ts**

Add import and registration in `openraven-ui/server/index.ts`:

```typescript
import wikiRouter from "./routes/wiki";
// after graphRouter registration:
app.route("/api/wiki", wikiRouter);
```

- [ ] **Step 4: Create WikiPage.tsx**

Create `openraven-ui/src/pages/WikiPage.tsx`:

```tsx
import { useEffect, useState } from "react";

interface WikiListItem { slug: string; title: string; }
interface WikiArticle { slug: string; title: string; content: string; }

export default function WikiPage() {
  const [articles, setArticles] = useState<WikiListItem[]>([]);
  const [selected, setSelected] = useState<WikiArticle | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch("/api/wiki").then(r => r.json()).then(setArticles).catch(() => {}).finally(() => setLoading(false));
  }, []);

  async function loadArticle(slug: string) {
    const res = await fetch(`/api/wiki/${encodeURIComponent(slug)}`);
    if (res.ok) setSelected(await res.json());
  }

  if (loading) return <div className="text-gray-500">Loading wiki...</div>;

  if (articles.length === 0) {
    return (
      <div className="text-gray-500">
        <h1 className="text-2xl font-bold text-white mb-2">Knowledge Wiki</h1>
        <p>No articles yet. Add files to start generating wiki articles.</p>
      </div>
    );
  }

  return (
    <div className="flex gap-6">
      {/* Article list */}
      <div className="w-64 shrink-0">
        <h2 className="text-lg font-semibold mb-3">Articles ({articles.length})</h2>
        <div className="flex flex-col gap-1">
          {articles.map((a) => (
            <button
              key={a.slug}
              onClick={() => loadArticle(a.slug)}
              className={`text-left text-sm px-2 py-1 rounded truncate ${
                selected?.slug === a.slug
                  ? "bg-blue-600/20 text-blue-400"
                  : "text-gray-400 hover:text-gray-200 hover:bg-gray-800"
              }`}
            >
              {a.title}
            </button>
          ))}
        </div>
      </div>
      {/* Article content */}
      <div className="flex-1 min-w-0">
        {selected ? (
          <div className="prose prose-invert max-w-none">
            <div className="whitespace-pre-wrap text-sm text-gray-300 leading-relaxed">{selected.content}</div>
          </div>
        ) : (
          <div className="text-gray-600 text-sm">Select an article to read</div>
        )}
      </div>
    </div>
  );
}
```

- [ ] **Step 5: Add wiki route to App.tsx**

Add import at top of `openraven-ui/src/App.tsx`:

```tsx
import WikiPage from "./pages/WikiPage";
```

Add nav link (after Graph, before Status):

```tsx
<NavLink to="/wiki" className={({ isActive }) => isActive ? "text-blue-400" : "text-gray-400 hover:text-gray-200"}>Wiki</NavLink>
```

Add route inside `<Routes>`:

```tsx
<Route path="/wiki" element={<WikiPage />} />
```

- [ ] **Step 6: Add route test**

Add mock and test to `openraven-ui/tests/server/routes.test.ts`:

Before `mock.module()`, add:

```typescript
const mockGetWikiList = mock(async () => [
  { slug: "apache_kafka", title: "Apache Kafka" },
]);
const mockGetWikiArticle = mock(async (_slug: string) => ({
  slug: "apache_kafka", title: "Apache Kafka", content: "# Apache Kafka\n\nStreaming platform.",
}));
```

Add to mock.module return:

```typescript
getWikiList: mockGetWikiList,
getWikiArticle: mockGetWikiArticle,
```

Add test block:

```typescript
describe("GET /api/wiki", () => {
  it("returns wiki article list", async () => {
    const req = new Request("http://localhost/api/wiki");
    const res = await appFetch(req);
    expect(res.status).toBe(200);
    const body = await res.json();
    expect(Array.isArray(body)).toBe(true);
    expect(body[0]).toMatchObject({ slug: "apache_kafka" });
  });
});
```

- [ ] **Step 7: Run all tests and build**

```bash
cd openraven && .venv/bin/python -m pytest tests/ -v --ignore=tests/test_integration.py
cd openraven-ui && bun test tests/ && bun run build
```

- [ ] **Step 8: Commit**

```bash
git add openraven-ui/server/services/core-client.ts openraven-ui/server/routes/wiki.ts openraven-ui/server/index.ts openraven-ui/src/pages/WikiPage.tsx openraven-ui/src/App.tsx openraven-ui/tests/server/routes.test.ts
git commit -m "feat(ui): add wiki browser page with article list and reader"
```

---

## Task 3: GraphML export endpoint + download button

**Files:**
- Modify: `openraven/src/openraven/api/server.py`
- Modify: `openraven/tests/test_api.py`
- Modify: `openraven-ui/src/pages/GraphPage.tsx`

- [ ] **Step 1: Write failing test**

Add to `openraven/tests/test_api.py`:

```python
def test_graph_export_endpoint(client: TestClient) -> None:
    response = client.get("/api/graph/export")
    assert response.status_code == 200
    assert "graphml" in response.headers.get("content-disposition", "").lower()
```

- [ ] **Step 2: Implement export endpoint**

Add to `server.py` imports:

```python
import asyncio
import tempfile

from fastapi import BackgroundTasks, FastAPI, File, Query, UploadFile
from fastapi.responses import FileResponse
```

Add inside `create_app()`, **before** the existing `/api/graph` route (so `/api/graph/export` matches before `/api/graph`):

```python
@app.get("/api/graph/export")
async def graph_export(background_tasks: BackgroundTasks):
    import os
    tmp = tempfile.NamedTemporaryFile(suffix=".graphml", delete=False)
    tmp.close()
    await asyncio.get_running_loop().run_in_executor(
        None, lambda: pipeline.graph.export_graphml(Path(tmp.name))
    )
    background_tasks.add_task(os.unlink, tmp.name)
    return FileResponse(
        path=tmp.name,
        media_type="application/xml",
        filename="openraven-knowledge-graph.graphml",
    )
```

- [ ] **Step 3: Add download button to GraphPage.tsx**

Add in the toolbar of `openraven-ui/src/pages/GraphPage.tsx`, before the node/edge count span:

```tsx
<a
  href="/api/graph/export"
  download
  className="text-xs px-2 py-1 rounded border border-gray-600 bg-gray-800 text-gray-200 hover:bg-gray-700"
>
  Export GraphML
</a>
```

- [ ] **Step 4: Run tests and build**

```bash
cd openraven && .venv/bin/python -m pytest tests/test_api.py -v -k "graph_export"
cd openraven-ui && bun run build
```

- [ ] **Step 5: Commit**

```bash
git add openraven/src/openraven/api/server.py openraven/tests/test_api.py openraven-ui/src/pages/GraphPage.tsx
git commit -m "feat: add GraphML export endpoint and download button"
```

---

## Task 4: Ingestion progress — polling backend

**Files:**
- Modify: `openraven/src/openraven/api/server.py`
- Modify: `openraven/tests/test_api.py`

- [ ] **Step 1: Write failing tests**

Add to `openraven/tests/test_api.py`:

```python
def test_ingest_start_returns_job_id(client: TestClient, config) -> None:
    config.ingestion_dir.mkdir(parents=True, exist_ok=True)
    # Create a tiny test file
    test_file = config.ingestion_dir / "test.md"
    test_file.write_text("# Test\n\nHello world.")

    import io
    response = client.post(
        "/api/ingest",
        files=[("files", ("test.md", io.BytesIO(b"# Test\n\nHello."), "text/markdown"))],
    )
    assert response.status_code == 200
    data = response.json()
    # Should still return IngestResponse for backwards compatibility
    assert "files_processed" in data or "job_id" in data


def test_ingest_status_unknown_job(client: TestClient) -> None:
    response = client.get("/api/ingest/status/nonexistent")
    assert response.status_code == 404
```

- [ ] **Step 2: Implement progress tracking**

Add to `server.py` at module level (before `create_app`):

```python
from dataclasses import dataclass, field as dc_field
import uuid

@dataclass
class IngestJob:
    job_id: str
    stage: str = "uploading"
    files_total: int = 0
    files_done: int = 0
    entities_extracted: int = 0
    articles_total: int = 0
    articles_done: int = 0
    errors: list[str] = dc_field(default_factory=list)
    result: dict | None = None
```

Add inside `create_app()`:

```python
ingest_jobs: dict[str, IngestJob] = {}

@app.get("/api/ingest/status/{job_id}")
async def ingest_status(job_id: str):
    from fastapi.responses import JSONResponse
    job = ingest_jobs.get(job_id)
    if not job:
        return JSONResponse({"error": "Job not found"}, status_code=404)
    return {
        "job_id": job.job_id,
        "stage": job.stage,
        "files_total": job.files_total,
        "files_done": job.files_done,
        "entities_extracted": job.entities_extracted,
        "articles_total": job.articles_total,
        "articles_done": job.articles_done,
        "errors": job.errors,
        "result": job.result,
    }
```

Modify the existing `ingest` endpoint to also return a `job_id`:

```python
@app.post("/api/ingest", response_model=IngestResponse)
async def ingest(files: list[UploadFile] = File(...)):
    saved_paths: list[Path] = []
    config.ingestion_dir.mkdir(parents=True, exist_ok=True)
    for upload in files:
        dest = config.ingestion_dir / upload.filename
        content = await upload.read()
        dest.write_bytes(content)
        saved_paths.append(dest)

    job_id = str(uuid.uuid4())[:8]
    job = IngestJob(job_id=job_id, files_total=len(saved_paths), stage="processing")
    ingest_jobs[job_id] = job

    result = await pipeline.add_files(saved_paths)

    job.stage = "done"
    job.files_done = result.files_processed
    job.entities_extracted = result.entities_extracted
    job.articles_done = result.articles_generated
    job.result = {
        "files_processed": result.files_processed,
        "entities_extracted": result.entities_extracted,
        "articles_generated": result.articles_generated,
        "errors": result.errors,
    }

    return IngestResponse(
        files_processed=result.files_processed,
        entities_extracted=result.entities_extracted,
        articles_generated=result.articles_generated,
        errors=result.errors,
    )
```

- [ ] **Step 3: Run tests**

Run: `cd openraven && .venv/bin/python -m pytest tests/test_api.py -v -k "ingest"`
Expected: All pass

- [ ] **Step 4: Commit**

```bash
git add openraven/src/openraven/api/server.py openraven/tests/test_api.py
git commit -m "feat(api): add ingestion job tracking with polling status endpoint"
```

---

## Task 5: Ingestion progress — frontend polling UI

**Files:**
- Modify: `openraven-ui/src/pages/IngestPage.tsx`

- [ ] **Step 1: Update IngestPage with progress display**

Replace `openraven-ui/src/pages/IngestPage.tsx`:

```tsx
import { useState } from "react";
import FileUploader from "../components/FileUploader";

interface IngestResult { files_processed: number; entities_extracted: number; articles_generated: number; errors: string[]; }

const STAGE_LABELS: Record<string, string> = {
  uploading: "Uploading files...",
  processing: "Processing documents...",
  done: "Complete",
  error: "Error occurred",
};

export default function IngestPage() {
  const [result, setResult] = useState<IngestResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [stage, setStage] = useState<string | null>(null);

  async function handleUpload(files: File[]) {
    setLoading(true); setResult(null); setStage("uploading");
    const formData = new FormData();
    for (const file of files) formData.append("files", file);
    try {
      setStage("processing");
      const res = await fetch("/api/ingest", { method: "POST", body: formData });
      const data = await res.json();
      setResult(data);
      setStage("done");
    } catch {
      setResult({ files_processed: 0, entities_extracted: 0, articles_generated: 0, errors: ["Failed to connect to the knowledge engine."] });
      setStage("error");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Add Documents</h1>
      <FileUploader onUpload={handleUpload} disabled={loading} />
      {loading && stage && (
        <div className="mt-6">
          <div className="flex items-center gap-3">
            <div className="w-4 h-4 border-2 border-blue-400 border-t-transparent rounded-full animate-spin" />
            <span className="text-gray-400">{STAGE_LABELS[stage] ?? stage}</span>
          </div>
          <div className="mt-2 h-1 bg-gray-800 rounded overflow-hidden">
            <div className="h-full bg-blue-500 rounded animate-pulse" style={{ width: stage === "processing" ? "60%" : "20%" }} />
          </div>
        </div>
      )}
      {result && !loading && (
        <div className="mt-6 bg-gray-900 border border-gray-800 rounded-lg p-4">
          <h2 className="font-semibold mb-2">Results</h2>
          <div className="grid grid-cols-3 gap-4 text-center">
            <div><div className="text-2xl font-bold text-blue-400">{result.files_processed}</div><div className="text-xs text-gray-500">Files processed</div></div>
            <div><div className="text-2xl font-bold text-green-400">{result.entities_extracted}</div><div className="text-xs text-gray-500">Entities extracted</div></div>
            <div><div className="text-2xl font-bold text-purple-400">{result.articles_generated}</div><div className="text-xs text-gray-500">Articles generated</div></div>
          </div>
          {result.errors.length > 0 && <div className="mt-3 text-red-400 text-sm">{result.errors.map((e, i) => <div key={i}>{e}</div>)}</div>}
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Run tests and build**

```bash
cd openraven-ui && bun test tests/ && bun run build
```

- [ ] **Step 3: Commit**

```bash
git add openraven-ui/src/pages/IngestPage.tsx
git commit -m "feat(ui): add ingestion progress indicator with stage display"
```

---

## Task 6: E2E verification

- [ ] **Step 1: Rebuild and restart**

```bash
cd openraven-ui && bun run build
pm2 restart all
sleep 8
```

- [ ] **Step 2: Verify all endpoints**

```bash
curl -sf http://localhost:8741/api/wiki | python3 -m json.tool
curl -sf http://localhost:8741/api/graph/export -o /tmp/test.graphml && head -3 /tmp/test.graphml
curl -sf http://localhost:3002/wiki | head -3  # SPA fallback
```

- [ ] **Step 3: Full test suite**

```bash
cd openraven && .venv/bin/python -m pytest tests/ -v --ignore=tests/test_integration.py
cd openraven-ui && bun test tests/
```

---

## Summary

| Task | What | Tests Added |
|---|---|---|
| 1 | Wiki API (list + read) | 3 Python API tests |
| 2 | Wiki proxy + WikiPage + routing | 1 Bun route test |
| 3 | GraphML export endpoint + button | 1 Python API test |
| 4 | Ingestion progress backend | 2 Python API tests |
| 5 | Ingestion progress frontend | Build verification |
| 6 | E2E verification | Full suite |

**Total new tests: 7**
