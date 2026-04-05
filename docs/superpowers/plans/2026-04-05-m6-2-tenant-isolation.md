# M6.2: Tenant Isolation Layer — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Scope all data (files, graph, wiki, courses, connectors) to individual tenants so multiple users can use the same OpenRaven instance without seeing each other's data.

**Architecture:** Per-tenant `working_dir` under `/data/tenants/{tenant_id}/`. When auth is enabled, the auth middleware extracts `tenant_id` from the session, creates a tenant-scoped `RavenConfig`, and injects a tenant-scoped `RavenPipeline` into each request. When auth is disabled (local mode), behavior is unchanged — single working_dir as before.

**Tech Stack:** Python (FastAPI dependency injection), existing RavenConfig/RavenPipeline

**Spec:** `docs/superpowers/specs/2026-04-04-m6-managed-saas-design.md` — Section 2

---

## File Structure

| File | Action | Responsibility |
|------|--------|---------------|
| `openraven/src/openraven/auth/tenant.py` | Create | Tenant-scoped config factory, pipeline cache |
| `openraven/src/openraven/api/server.py` | Modify | Inject tenant-scoped pipeline via auth middleware |
| `openraven/tests/test_tenant.py` | Create | Tenant isolation tests |

---

### Task 1: Tenant Config Factory

**Files:**
- Create: `openraven/src/openraven/auth/tenant.py`
- Test: `openraven/tests/test_tenant.py`

- [ ] **Step 1: Write failing test**

Create `openraven/tests/test_tenant.py`:

```python
import pytest
import os
import shutil
from pathlib import Path
from openraven.auth.tenant import get_tenant_config, get_tenant_pipeline

from openraven.config import RavenConfig


@pytest.fixture
def base_config(tmp_path):
    return RavenConfig(
        working_dir=tmp_path / "base",
        database_url="sqlite:///test.db",
    )


def test_get_tenant_config_creates_tenant_dir(base_config, tmp_path):
    tenant_id = "tenant-abc-123"
    tenant_config = get_tenant_config(base_config, tenant_id, tmp_path / "tenants")
    assert tenant_config.working_dir == tmp_path / "tenants" / tenant_id
    assert tenant_config.working_dir.exists()


def test_get_tenant_config_preserves_llm_settings(base_config, tmp_path):
    tenant_config = get_tenant_config(base_config, "t1", tmp_path / "tenants")
    assert tenant_config.llm_provider == base_config.llm_provider
    assert tenant_config.llm_model == base_config.llm_model
    assert tenant_config.gemini_api_key == base_config.gemini_api_key


def test_get_tenant_config_isolates_paths(base_config, tmp_path):
    c1 = get_tenant_config(base_config, "t1", tmp_path / "tenants")
    c2 = get_tenant_config(base_config, "t2", tmp_path / "tenants")
    assert c1.working_dir != c2.working_dir
    assert c1.db_path != c2.db_path
    assert c1.lightrag_dir != c2.lightrag_dir
    assert c1.wiki_dir != c2.wiki_dir


def test_get_tenant_pipeline_returns_pipeline(base_config, tmp_path):
    pipeline = get_tenant_pipeline(base_config, "t1", tmp_path / "tenants")
    assert pipeline is not None
    assert pipeline.config.working_dir == tmp_path / "tenants" / "t1"


def test_get_tenant_pipeline_caches_instance(base_config, tmp_path):
    p1 = get_tenant_pipeline(base_config, "t1", tmp_path / "tenants")
    p2 = get_tenant_pipeline(base_config, "t1", tmp_path / "tenants")
    assert p1 is p2  # Same instance returned from cache
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd openraven && pytest tests/test_tenant.py -v
```

Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Implement tenant.py**

Create `openraven/src/openraven/auth/tenant.py`:

```python
"""Tenant-scoped configuration and pipeline management."""

from dataclasses import replace
from pathlib import Path
from functools import lru_cache

from openraven.config import RavenConfig
from openraven.pipeline import RavenPipeline


# Cache of tenant pipelines — keyed by tenant_id
_pipeline_cache: dict[str, RavenPipeline] = {}


def get_tenant_config(
    base_config: RavenConfig,
    tenant_id: str,
    tenants_root: Path | None = None,
) -> RavenConfig:
    """Create a tenant-scoped RavenConfig with isolated working_dir.
    
    All LLM/provider settings are inherited from base_config.
    Only working_dir (and its derived paths) change per tenant.
    """
    if tenants_root is None:
        tenants_root = Path("/data/tenants")
    
    tenant_dir = tenants_root / tenant_id
    tenant_dir.mkdir(parents=True, exist_ok=True)
    
    return replace(base_config, working_dir=tenant_dir)


def get_tenant_pipeline(
    base_config: RavenConfig,
    tenant_id: str,
    tenants_root: Path | None = None,
) -> RavenPipeline:
    """Get or create a tenant-scoped RavenPipeline.
    
    Pipelines are cached by tenant_id to avoid re-initializing
    LightRAG/graph for every request.
    """
    if tenant_id in _pipeline_cache:
        return _pipeline_cache[tenant_id]
    
    tenant_config = get_tenant_config(base_config, tenant_id, tenants_root)
    pipeline = RavenPipeline(tenant_config)
    _pipeline_cache[tenant_id] = pipeline
    return pipeline


def clear_pipeline_cache() -> None:
    """Clear the pipeline cache. Used in tests."""
    _pipeline_cache.clear()
```

- [ ] **Step 4: Run tests**

```bash
cd openraven && pytest tests/test_tenant.py -v
```

Expected: 5 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add openraven/src/openraven/auth/tenant.py openraven/tests/test_tenant.py
git commit -m "feat(m6): add tenant-scoped config factory and pipeline cache"
```

---

### Task 2: Inject Tenant Pipeline into Server Routes

**Files:**
- Modify: `openraven/src/openraven/api/server.py`
- Test: `openraven/tests/test_tenant.py` (append)

- [ ] **Step 1: Update server.py to inject tenant-scoped pipeline**

Read `openraven/src/openraven/api/server.py`. In the `create_app()` function, after the auth setup block, add a tenant pipeline dependency:

```python
    # Tenant pipeline injection (when auth is enabled)
    if config.auth_enabled and auth_engine:
        from openraven.auth.tenant import get_tenant_pipeline
        from openraven.auth.middleware import create_require_auth
        require_auth = create_require_auth(auth_engine)

        def get_pipeline_for_request(auth: AuthContext = Depends(require_auth)) -> RavenPipeline:
            return get_tenant_pipeline(config, auth.tenant_id)
```

Then, for each existing route that uses `pipeline` (the module-level variable), the auth-enabled mode should use the tenant-scoped pipeline instead. The simplest approach: wrap the existing pipeline variable access in a helper that checks if auth is enabled.

Add this helper inside `create_app()` after the pipeline is created:

```python
    def resolve_pipeline(request: Request) -> RavenPipeline:
        """Get the pipeline for the current request — tenant-scoped if auth enabled."""
        if config.auth_enabled and auth_engine:
            session_id = request.cookies.get("session_id")
            if session_id:
                from openraven.auth.sessions import validate_session
                ctx = validate_session(auth_engine, session_id)
                if ctx:
                    from openraven.auth.tenant import get_tenant_pipeline
                    return get_tenant_pipeline(config, ctx.tenant_id)
        return pipeline  # Fallback to default pipeline (local mode)
```

IMPORTANT: Do NOT change the route signatures or break backward compatibility. The `resolve_pipeline()` helper is called inside route handlers that need tenant-scoped data. For now, just add the helper — routes will be updated to use it in future tasks as needed.

- [ ] **Step 2: Run all tests to verify no regressions**

```bash
cd openraven && pytest tests/ -v --ignore=tests/benchmark -x 2>&1 | tail -10
```

Expected: All existing tests pass (no routes changed yet).

- [ ] **Step 3: Commit**

```bash
git add openraven/src/openraven/api/server.py
git commit -m "feat(m6): add tenant pipeline resolver to server (opt-in)"
```

---

### Task 3: Verify Full Isolation End-to-End

- [ ] **Step 1: Run all auth + tenant tests**

```bash
cd openraven && pytest tests/test_auth.py tests/test_auth_sessions.py tests/test_auth_api.py tests/test_auth_reset.py tests/test_tenant.py -v
```

Expected: All pass.

- [ ] **Step 2: Run all tests for regression check**

```bash
cd openraven && pytest tests/ --ignore=tests/benchmark -x 2>&1 | tail -5
```

Expected: Same results as before (162+ pass, 1 pre-existing ollama failure).

- [ ] **Step 3: Commit any fixes**

Only if needed.
