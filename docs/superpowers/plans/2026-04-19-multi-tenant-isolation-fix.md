# Multi-Tenant Isolation Fix Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace all direct access to global `config`/`pipeline` variables in API endpoints with FastAPI `Depends()` dependency injection, ensuring every endpoint is tenant-scoped.

**Architecture:** Define two dependency functions (`get_tenant_config`, `get_tenant_pipeline`) inside `create_app()`, then migrate all ~30 endpoints to use `Depends()`. Delete the old `resolve_config`/`resolve_pipeline` functions. Fix `get_recent_messages()` to require `tenant_id`. This ensures new endpoints cannot accidentally access another tenant's data.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy Core, networkx

---

## File Structure

| File | Action | Responsibility |
|------|--------|---------------|
| `openraven/src/openraven/api/server.py` | Modify | Define dependency functions, migrate all endpoints, delete old helpers |
| `openraven/src/openraven/conversations/models.py` | Modify | Add `tenant_id` param to `get_recent_messages()` |
| `openraven/src/openraven/conversations/routes.py` | Modify | Pass `tenant_id` to `get_recent_messages()` |
| `openraven/tests/test_conversations.py` | Modify | Update `get_recent_messages()` call signatures |
| `openraven/tests/test_graph.py` | Verify | Confirm existing tests still pass |

---

### Task 1: Define dependency functions and migrate status/ask endpoints

This is the foundational task — define the new dependency functions and prove they work by migrating the two most commonly used endpoints.

**Files:**
- Modify: `openraven/src/openraven/api/server.py`

- [ ] **Step 1: Add dependency function imports at the top of create_app()**

In `server.py`, inside `create_app()`, find the auth setup block (around line 124). After `auth_engine = None` is potentially set, add these imports right after the existing `from openraven.auth.sessions import validate_session as _validate_session` (line 152):

```python
from openraven.auth.sessions import validate_session as _validate_session
from openraven.auth.tenant import get_tenant_config as _get_tenant_config_fn
from openraven.auth.tenant import get_tenant_pipeline as _get_tenant_pipeline_fn
```

Note: these imports are already conditionally done inside `resolve_config`/`resolve_pipeline`. We move them to the top of the auth block so the dependency functions can use them.

- [ ] **Step 2: Define dependency functions**

Replace the existing `resolve_config` and `resolve_pipeline` functions (lines 198-220) with:

```python
    async def get_tenant_config(request: Request) -> RavenConfig:
        """FastAPI dependency: returns tenant-scoped config. Cached per-request by FastAPI."""
        if config.auth_enabled and auth_engine:
            session_id = request.cookies.get("session_id")
            if session_id:
                ctx = _validate_session(auth_engine, session_id)
                if ctx:
                    return _get_tenant_config_fn(
                        config, ctx.tenant_id,
                        tenants_root=Path(config.working_dir).parent,
                        demo_theme=ctx.demo_theme,
                    )
        return config

    async def get_tenant_pipeline(request: Request) -> RavenPipeline:
        """FastAPI dependency: returns tenant-scoped pipeline. Cached per-request by FastAPI."""
        if config.auth_enabled and auth_engine:
            session_id = request.cookies.get("session_id")
            if session_id:
                ctx = _validate_session(auth_engine, session_id)
                if ctx:
                    return _get_tenant_pipeline_fn(
                        config, ctx.tenant_id,
                        tenants_root=Path(config.working_dir).parent,
                        demo_theme=ctx.demo_theme,
                    )
        return pipeline
```

- [ ] **Step 3: Migrate GET /api/status**

Replace:
```python
    @app.get("/api/status", response_model=StatusResponse)
    async def status():
        report = pipeline.get_health_report()
```

With:
```python
    @app.get("/api/status", response_model=StatusResponse)
    async def status(pipe: RavenPipeline = Depends(get_tenant_pipeline)):
        report = pipe.get_health_report()
```

- [ ] **Step 4: Migrate POST /api/ask**

Replace:
```python
    @app.post("/api/ask", response_model=AskResponse)
    async def ask(request: Request, req: AskRequest):
        pipe = resolve_pipeline(request)
```

With:
```python
    @app.post("/api/ask", response_model=AskResponse)
    async def ask(request: Request, req: AskRequest, pipe: RavenPipeline = Depends(get_tenant_pipeline)):
```

And delete the line `pipe = resolve_pipeline(request)`.

- [ ] **Step 5: Add Depends import**

At the top of `server.py`, find the FastAPI imports (line 13) and add `Depends`:

```python
from fastapi import BackgroundTasks, Depends, FastAPI, File, Form, Query, Request, UploadFile
```

- [ ] **Step 6: Run tests to verify no breakage**

```bash
cd /home/ubuntu/source/OpenRaven/openraven && source .venv/bin/activate
pytest tests/test_graph.py -v
```

Expected: All 24 PASS

- [ ] **Step 7: Commit**

```bash
cd /home/ubuntu/source/OpenRaven
git add openraven/src/openraven/api/server.py
git commit -m "refactor(api): define tenant dependency functions, migrate status+ask endpoints"
```

---

### Task 2: Migrate ingest and graph/wiki export endpoints

These are the HIGH-risk endpoints identified in the audit.

**Files:**
- Modify: `openraven/src/openraven/api/server.py`

- [ ] **Step 1: Migrate POST /api/ingest**

Replace:
```python
    async def ingest(request: Request, files: list[UploadFile] = File(...), schema: str | None = Form(default=None)):
        schema_name: str | None = schema if schema and schema != "auto" else None

        saved_paths: list[Path] = []
        config.ingestion_dir.mkdir(parents=True, exist_ok=True)
```

With:
```python
    async def ingest(request: Request, files: list[UploadFile] = File(...), schema: str | None = Form(default=None), cfg: RavenConfig = Depends(get_tenant_config), pipe: RavenPipeline = Depends(get_tenant_pipeline)):
        schema_name: str | None = schema if schema and schema != "auto" else None

        saved_paths: list[Path] = []
        cfg.ingestion_dir.mkdir(parents=True, exist_ok=True)
```

Also replace within the same function:
- `config.ingestion_dir / safe_name` → `cfg.ingestion_dir / safe_name`
- `await pipeline.add_files(saved_paths` → `await pipe.add_files(saved_paths`

- [ ] **Step 2: Migrate GET /api/graph/export**

Replace:
```python
    @app.get("/api/graph/export")
    async def graph_export(background_tasks: BackgroundTasks):
        import os
        tmp = tempfile.NamedTemporaryFile(suffix=".graphml", delete=False)
        tmp.close()
        await asyncio.get_running_loop().run_in_executor(
            None, lambda: pipeline.graph.export_graphml(Path(tmp.name))
        )
```

With:
```python
    @app.get("/api/graph/export")
    async def graph_export(background_tasks: BackgroundTasks, pipe: RavenPipeline = Depends(get_tenant_pipeline)):
        import os
        tmp = tempfile.NamedTemporaryFile(suffix=".graphml", delete=False)
        tmp.close()
        await asyncio.get_running_loop().run_in_executor(
            None, lambda: pipe.graph.export_graphml(Path(tmp.name))
        )
```

- [ ] **Step 3: Migrate GET /api/wiki/export**

Replace:
```python
    @app.get("/api/wiki/export")
    async def wiki_export(background_tasks: BackgroundTasks):
        """Download all wiki articles as a zip of markdown files."""
        import os
        import zipfile
        wiki_dir = config.wiki_dir
```

With:
```python
    @app.get("/api/wiki/export")
    async def wiki_export(background_tasks: BackgroundTasks, cfg: RavenConfig = Depends(get_tenant_config)):
        """Download all wiki articles as a zip of markdown files."""
        import os
        import zipfile
        wiki_dir = cfg.wiki_dir
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/test_graph.py -v
```

Expected: All 24 PASS

- [ ] **Step 5: Commit**

```bash
git add openraven/src/openraven/api/server.py
git commit -m "fix(api): tenant-scope ingest, graph export, wiki export endpoints"
```

---

### Task 3: Migrate graph, wiki, and discovery endpoints

These endpoints already used `resolve_config`/`resolve_pipeline` — migrate to `Depends` for consistency.

**Files:**
- Modify: `openraven/src/openraven/api/server.py`

- [ ] **Step 1: Migrate GET /api/graph**

Replace:
```python
    @app.get("/api/graph", response_model=GraphResponse)
    async def graph(request: Request, max_nodes: int = Query(default=500, ge=1, le=5000)):
        pipe = resolve_pipeline(request)
        data = await asyncio.get_event_loop().run_in_executor(
            None, lambda: pipe.graph.get_graph_data(max_nodes=max_nodes)
        )
```

With:
```python
    @app.get("/api/graph", response_model=GraphResponse)
    async def graph(max_nodes: int = Query(default=500, ge=1, le=5000), pipe: RavenPipeline = Depends(get_tenant_pipeline)):
        data = await asyncio.get_running_loop().run_in_executor(
            None, lambda: pipe.graph.get_graph_data(max_nodes=max_nodes)
        )
```

- [ ] **Step 2: Migrate GET /api/graph/subgraph**

Replace:
```python
    @app.get("/api/graph/subgraph")
    async def graph_subgraph(
        request: Request,
        entities: str | None = Query(default=None),
        files: str | None = Query(default=None),
        max_nodes: int = Query(default=30, ge=1, le=200),
    ):
        pipe = resolve_pipeline(request)
```

With:
```python
    @app.get("/api/graph/subgraph")
    async def graph_subgraph(
        entities: str | None = Query(default=None),
        files: str | None = Query(default=None),
        max_nodes: int = Query(default=30, ge=1, le=200),
        pipe: RavenPipeline = Depends(get_tenant_pipeline),
    ):
```

And delete the line `pipe = resolve_pipeline(request)`.

- [ ] **Step 3: Migrate GET /api/graph/node/{node_id}/context**

Replace:
```python
    @app.get("/api/graph/node/{node_id}/context")
    async def graph_node_context(request: Request, node_id: str):
        pipe = resolve_pipeline(request)
        search_dirs = [pipe.config.working_dir, pipe.config.working_dir.parent]
```

With:
```python
    @app.get("/api/graph/node/{node_id}/context")
    async def graph_node_context(node_id: str, pipe: RavenPipeline = Depends(get_tenant_pipeline)):
        search_dirs = [pipe.config.working_dir, pipe.config.working_dir.parent]
```

- [ ] **Step 4: Migrate GET /api/wiki and GET /api/wiki/{slug}**

For `/api/wiki`, replace:
```python
        rcfg = resolve_config(request)
```
With adding `cfg: RavenConfig = Depends(get_tenant_config)` to the function signature and using `cfg` instead of `rcfg`.

Do the same for `/api/wiki/{slug}`.

- [ ] **Step 5: Migrate GET /api/discovery**

Replace:
```python
    @app.get("/api/discovery", response_model=list[DiscoveryInsightResponse])
    async def discovery():
        from openraven.discovery.analyzer import analyze_themes
        graph_stats = pipeline.graph.get_detailed_stats()
```

With:
```python
    @app.get("/api/discovery", response_model=list[DiscoveryInsightResponse])
    async def discovery(pipe: RavenPipeline = Depends(get_tenant_pipeline)):
        from openraven.discovery.analyzer import analyze_themes
        graph_stats = pipe.graph.get_detailed_stats()
```

- [ ] **Step 6: Run tests**

```bash
pytest tests/test_graph.py -v
```

Expected: All 24 PASS

- [ ] **Step 7: Commit**

```bash
git add openraven/src/openraven/api/server.py
git commit -m "refactor(api): migrate graph, wiki, discovery endpoints to Depends"
```

---

### Task 4: Migrate connector endpoints

These endpoints need both `cfg` and `pipe` for tenant-scoped Google token paths and ingestion directories.

**Files:**
- Modify: `openraven/src/openraven/api/server.py`

- [ ] **Step 1: Migrate GET /api/connectors/status**

Replace:
```python
    @app.get("/api/connectors/status")
    async def connectors_status():
        from openraven.connectors.google_auth import load_token
        token = load_token(config.google_token_path)
        google_connected = token is not None
        return {
            "gdrive": {"connected": google_connected},
            "gmail": {"connected": google_connected},
            "meet": {"connected": google_connected},
            "otter": {"connected": bool(config.otter_api_key)},
            "google_configured": bool(config.google_client_id and config.google_client_secret),
        }
```

With:
```python
    @app.get("/api/connectors/status")
    async def connectors_status(cfg: RavenConfig = Depends(get_tenant_config)):
        from openraven.connectors.google_auth import load_token
        token = load_token(cfg.google_token_path)
        google_connected = token is not None
        return {
            "gdrive": {"connected": google_connected},
            "gmail": {"connected": google_connected},
            "meet": {"connected": google_connected},
            "otter": {"connected": bool(cfg.otter_api_key)},
            "google_configured": bool(cfg.google_client_id and cfg.google_client_secret),
        }
```

- [ ] **Step 2: Migrate GET /api/connectors/google/auth-url**

Replace `config.google_client_id` with `cfg.google_client_id`. Add `cfg: RavenConfig = Depends(get_tenant_config)` to signature.

- [ ] **Step 3: Migrate GET /api/connectors/google/callback**

Replace all `config.*` with `cfg.*`. Add `cfg: RavenConfig = Depends(get_tenant_config)` to signature.

- [ ] **Step 4: Migrate POST /api/connectors/gdrive/sync**

Replace:
```python
    @app.post("/api/connectors/gdrive/sync")
    async def gdrive_sync():
```

With:
```python
    @app.post("/api/connectors/gdrive/sync")
    async def gdrive_sync(cfg: RavenConfig = Depends(get_tenant_config), pipe: RavenPipeline = Depends(get_tenant_pipeline)):
```

Then replace all `config.*` with `cfg.*` and `pipeline.add_files` with `pipe.add_files` within the function.

- [ ] **Step 5: Migrate gmail/meet/otter sync the same way**

Apply the same pattern to:
- `POST /api/connectors/gmail/sync` — add `cfg + pipe` Depends, replace `config.*` → `cfg.*`, `pipeline.*` → `pipe.*`
- `POST /api/connectors/meet/sync` — same
- `POST /api/connectors/otter/sync` — same
- `POST /api/connectors/otter/save-key` — add `cfg` Depends, replace `config.otter_key_path` → `cfg.otter_key_path`

- [ ] **Step 6: Run tests**

```bash
pytest tests/test_graph.py tests/test_connectors.py -v 2>&1 | tail -5
```

Expected: All PASS (or pre-existing failures only)

- [ ] **Step 7: Commit**

```bash
git add openraven/src/openraven/api/server.py
git commit -m "fix(api): tenant-scope all connector endpoints with Depends"
```

---

### Task 5: Migrate agent endpoints

Remove global `agents_dir`, use `cfg.working_dir / "agents"` inside each endpoint.

**Files:**
- Modify: `openraven/src/openraven/api/server.py`

- [ ] **Step 1: Delete global agents_dir**

Delete these two lines (around line 678):
```python
    agents_dir = config.working_dir / "agents"
    agents_dir.mkdir(parents=True, exist_ok=True)
```

- [ ] **Step 2: Migrate POST /api/agents**

Replace:
```python
    @app.post("/api/agents")
    async def create_agent_endpoint(body: dict):
```

With:
```python
    @app.post("/api/agents")
    async def create_agent_endpoint(body: dict, cfg: RavenConfig = Depends(get_tenant_config)):
```

Inside the function, replace:
- `agents_dir` → `cfg.working_dir / "agents"` (assign to local var `tenant_agents_dir` for readability)
- `config.working_dir` → `cfg.working_dir`
- Add `tenant_agents_dir.mkdir(parents=True, exist_ok=True)` at the start

- [ ] **Step 3: Migrate all remaining agent endpoints**

Apply the same pattern to each:
- `GET /api/agents` — add `cfg` Depends, `agents_dir` → `(cfg.working_dir / "agents")`
- `GET /api/agents/{agent_id}` — same
- `DELETE /api/agents/{agent_id}` — same
- `POST /api/agents/{agent_id}/tokens` — same
- `POST /api/agents/{agent_id}/deploy` — add `cfg` Depends, replace `config.api_port` → `cfg.api_port`, `config.working_dir` → `cfg.working_dir`
- `POST /api/agents/{agent_id}/undeploy` — same
- `GET /agents/{agent_id}` (public) — this uses `agents_dir` but has no auth context. Keep using global `config.working_dir / "agents"` for public agent pages.
- `GET /agents/{agent_id}/info` (public) — same, keep global
- `POST /agents/{agent_id}/ask` (public) — replace `pipeline.ask_with_sources` → needs special handling (public endpoint uses global pipeline, that's correct for agents — agents serve their own KB)

- [ ] **Step 4: Run tests**

```bash
pytest tests/test_graph.py tests/test_agents.py -v 2>&1 | tail -5
```

Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add openraven/src/openraven/api/server.py
git commit -m "fix(api): tenant-scope agent endpoints, remove global agents_dir"
```

---

### Task 6: Migrate course endpoints

Course generation also uses global `config` and `pipeline`.

**Files:**
- Modify: `openraven/src/openraven/api/server.py`

- [ ] **Step 1: Migrate POST /api/courses/generate**

Replace:
```python
    @app.post("/api/courses/generate")
    async def courses_generate(body: dict):
```

With:
```python
    @app.post("/api/courses/generate")
    async def courses_generate(body: dict, cfg: RavenConfig = Depends(get_tenant_config), pipe: RavenPipeline = Depends(get_tenant_pipeline)):
```

Inside the function, replace:
- `config.ollama_base_url` → `cfg.ollama_base_url`
- `config.llm_provider` → `cfg.llm_provider`
- `pipeline.graph.get_stats()` → `pipe.graph.get_stats()`
- `config.llm_api_key` → `cfg.llm_api_key`
- `config.llm_model` → `cfg.llm_model`
- `config.courses_dir` → `cfg.courses_dir`
- `pipeline.ask_with_sources` → `pipe.ask_with_sources`

- [ ] **Step 2: Migrate GET /api/courses and other course endpoints**

- `GET /api/courses` — add `cfg` Depends, `config.courses_dir` → `cfg.courses_dir`
- `GET /api/courses/{course_id}` — same
- `GET /api/courses/{course_id}/download` — same
- `DELETE /api/courses/{course_id}` — same

- [ ] **Step 3: Run tests**

```bash
pytest tests/test_graph.py tests/test_courses.py -v 2>&1 | tail -5
```

Expected: All PASS

- [ ] **Step 4: Commit**

```bash
git add openraven/src/openraven/api/server.py
git commit -m "fix(api): tenant-scope course generation endpoints"
```

---

### Task 7: Fix get_recent_messages tenant isolation

**Files:**
- Modify: `openraven/src/openraven/conversations/models.py`
- Modify: `openraven/src/openraven/conversations/routes.py`
- Modify: `openraven/src/openraven/api/server.py`
- Modify: `openraven/tests/test_conversations.py`

- [ ] **Step 1: Update get_recent_messages signature and query**

In `openraven/src/openraven/conversations/models.py`, replace:

```python
def get_recent_messages(
    engine: Engine,
    conversation_id: str,
    limit: int = 20,
) -> list[dict]:
    """Get the most recent messages for a conversation, in chronological order."""
    with engine.connect() as conn:
        rows = conn.execute(
            select(messages)
            .where(messages.c.conversation_id == conversation_id)
            .order_by(desc(messages.c.created_at))
            .limit(limit)
        ).fetchall()
```

With:

```python
def get_recent_messages(
    engine: Engine,
    conversation_id: str,
    tenant_id: str | None = None,
    limit: int = 20,
) -> list[dict]:
    """Get the most recent messages for a conversation, in chronological order."""
    with engine.connect() as conn:
        query = (
            select(messages)
            .where(messages.c.conversation_id == conversation_id)
        )
        if tenant_id:
            query = query.join(
                conversations, messages.c.conversation_id == conversations.c.id
            ).where(conversations.c.tenant_id == tenant_id)
        rows = conn.execute(
            query.order_by(desc(messages.c.created_at)).limit(limit)
        ).fetchall()
```

Note: need to import `conversations` table at the top of the file if not already imported.

- [ ] **Step 2: Update caller in conversations/routes.py**

In `openraven/src/openraven/conversations/routes.py`, line 67, replace:

```python
        msgs = get_recent_messages(engine, convo_id, limit=200)
```

With:

```python
        msgs = get_recent_messages(engine, convo_id, tenant_id=ctx.tenant_id, limit=200)
```

- [ ] **Step 3: Update caller in server.py**

In `server.py`, around line 276, replace:

```python
                db_msgs = get_recent_messages(auth_engine, req.conversation_id, limit=20)
```

With:

```python
                db_msgs = get_recent_messages(auth_engine, req.conversation_id, tenant_id=ctx.tenant_id, limit=20)
```

- [ ] **Step 4: Update tests**

In `openraven/tests/test_conversations.py`, find all calls to `get_recent_messages` and add `tenant_id` parameter. The tests create conversations with a known tenant_id, so pass that:

```python
# Replace:
msgs = get_recent_messages(engine, convo_id, limit=20)
# With:
msgs = get_recent_messages(engine, convo_id, tenant_id="test-tenant", limit=20)
```

- [ ] **Step 5: Run conversation tests**

```bash
pytest tests/test_conversations.py -v
```

Expected: All PASS

- [ ] **Step 6: Commit**

```bash
git add openraven/src/openraven/conversations/models.py openraven/src/openraven/conversations/routes.py openraven/src/openraven/api/server.py openraven/tests/test_conversations.py
git commit -m "fix(conversations): add tenant_id to get_recent_messages for cross-tenant isolation"
```

---

### Task 8: Delete old resolve functions and verify

Final cleanup — remove the old functions and run full test suite.

**Files:**
- Modify: `openraven/src/openraven/api/server.py`

- [ ] **Step 1: Delete resolve_config and resolve_pipeline**

Search for and delete the old `resolve_config` function definition (if still present after Task 1 replacements). Also delete `resolve_pipeline`.

- [ ] **Step 2: Verify no remaining references to old functions**

```bash
cd /home/ubuntu/source/OpenRaven
grep -n "resolve_config\|resolve_pipeline" openraven/src/openraven/api/server.py
```

Expected: No matches (or only in comments)

- [ ] **Step 3: Verify no remaining direct config/pipeline access in endpoints**

```bash
grep -n "= pipeline\.\|= config\." openraven/src/openraven/api/server.py | grep -v "def \|#\|async def\|get_tenant"
```

Expected: Only matches inside `get_tenant_config`/`get_tenant_pipeline` dependency functions (where they access the closure variable)

- [ ] **Step 4: Run full test suite**

```bash
cd /home/ubuntu/source/OpenRaven/openraven && source .venv/bin/activate
pytest tests/test_graph.py tests/test_conversations.py tests/test_demo.py tests/test_auth.py -v 2>&1 | tail -20
```

Expected: All PASS (excluding pre-existing failures)

- [ ] **Step 5: Verify live APIs still work**

```bash
curl -s http://localhost:8741/health | python3 -m json.tool
curl -s http://localhost:8741/api/demo/themes | python3 -c "import sys,json; print(len(json.load(sys.stdin)), 'themes')"
```

Expected: Health OK, 4 themes listed

- [ ] **Step 6: Commit**

```bash
git add openraven/src/openraven/api/server.py
git commit -m "refactor(api): delete old resolve_config/resolve_pipeline, cleanup complete"
```
