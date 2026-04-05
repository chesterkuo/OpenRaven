# M7.7 Package Publishing + M7.5 Audit Logs Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `pip install openraven` work with the `raven` CLI, and add PostgreSQL-backed audit logging for SaaS mode.

**Architecture:** M7.7 fixes the existing `pyproject.toml` (missing deps, entry point path) and validates installation in a clean venv. M7.5 adds an `audit/` module following the existing auth module pattern (SQLAlchemy table + Alembic migration + FastAPI routes), with `log_action()` calls wired into existing endpoints.

**Tech Stack:** Python 3.12, hatchling (build), SQLAlchemy (audit table), Alembic (migration), FastAPI (audit routes)

---

## File Structure

| File | Action | Responsibility |
|------|--------|---------------|
| `openraven/pyproject.toml` | Modify | Fix deps, entry point, add `openai` |
| `openraven/src/openraven/audit/__init__.py` | Create | Package marker |
| `openraven/src/openraven/audit/logger.py` | Create | `log_action()` function |
| `openraven/src/openraven/audit/routes.py` | Create | GET /api/audit, GET /api/audit/export |
| `openraven/src/openraven/auth/db.py` | Modify | Add `audit_logs` table definition |
| `openraven/alembic/versions/003_audit_logs.py` | Create | Migration for audit_logs table |
| `openraven/src/openraven/api/server.py` | Modify | Wire audit routes + log_action calls |
| `openraven/src/openraven/auth/routes.py` | Modify | Add log_action calls to auth endpoints |
| `openraven/tests/test_audit.py` | Create | Audit logger + route tests |
| `openraven-ui/src/pages/AuditLogPage.tsx` | Create | Audit log viewer UI |
| `openraven-ui/src/App.tsx` | Modify | Add /audit route |

---

## Task 1: Fix pyproject.toml for PyPI Publishing

**Files:**
- Modify: `openraven/pyproject.toml`

- [ ] **Step 1: Update pyproject.toml with missing dependencies and correct entry point**

Edit `openraven/pyproject.toml`. The current `dependencies` list is missing `openai` (used by parser.py and discovery analyzer). Also add project URLs and classifiers for PyPI page:

```toml
[project]
name = "openraven"
version = "0.1.0"
description = "AI-powered personal professional knowledge asset platform"
readme = "README.md"
license = "Apache-2.0"
requires-python = ">=3.12"
keywords = ["knowledge-management", "rag", "lightrag", "knowledge-graph", "ai"]
classifiers = [
    "Development Status :: 3 - Alpha",
    "License :: OSI Approved :: Apache Software License",
    "Programming Language :: Python :: 3.12",
    "Topic :: Scientific/Engineering :: Artificial Intelligence",
]
dependencies = [
    "langextract>=0.1.0",
    "lightrag-hku>=1.0.0",
    "docling>=2.0.0",
    "fastapi>=0.115.0",
    "uvicorn[standard]>=0.30.0",
    "click>=8.1.0",
    "openai>=1.0.0",
    "google-genai>=1.0.0",
    "httpx>=0.27.0",
    "pydantic>=2.0.0",
    "networkx>=3.0",
    "jinja2>=3.1.0",
    "google-auth>=2.0.0",
    "google-auth-oauthlib>=1.0.0",
    "google-api-python-client>=2.0.0",
    "asyncpg>=0.29.0",
    "sqlalchemy[asyncio]>=2.0.0",
    "bcrypt>=4.1.0",
    "alembic>=1.13.0",
    "python-multipart>=0.0.9",
    "neo4j>=5.0.0",
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
ollama = ["ollama"]

[project.urls]
Homepage = "https://github.com/chesterkuo/OpenRaven"
Repository = "https://github.com/chesterkuo/OpenRaven"
Issues = "https://github.com/chesterkuo/OpenRaven/issues"

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

Key changes from current:
- Added `"openai>=1.0.0"` to dependencies (used by parser.py, discovery analyzer)
- Kept `requires-python >= 3.12` (matches ruff target-version and codebase)
- Removed `"anthropic>=0.40.0"` (not used — codebase uses Gemini, not Anthropic)
- Added `keywords`, `classifiers`, `[project.urls]`
- Added `ollama` optional dependency group

- [ ] **Step 2: Verify the package builds**

```bash
cd /home/ubuntu/source/OpenRaven/openraven && python3 -m build 2>&1 | tail -10
```
Expected: Build succeeds, creates `dist/openraven-0.1.0-py3-none-any.whl`

If `build` is not installed:
```bash
pip install build && python3 -m build 2>&1 | tail -10
```

- [ ] **Step 3: Test installation in a temporary venv**

```bash
cd /home/ubuntu/source/OpenRaven/openraven && python3 -m venv /tmp/test-openraven && /tmp/test-openraven/bin/pip install dist/openraven-0.1.0-py3-none-any.whl 2>&1 | tail -5 && /tmp/test-openraven/bin/raven --help && /tmp/test-openraven/bin/python -c "from openraven.pipeline import RavenPipeline; print('Import OK')" && rm -rf /tmp/test-openraven
```
Expected: `raven --help` shows all commands, import succeeds.

- [ ] **Step 4: Commit**

```bash
cd /home/ubuntu/source/OpenRaven && git add openraven/pyproject.toml && git commit -m "feat(m7): fix pyproject.toml for PyPI publishing

Add missing openai dependency, lower Python requirement to 3.11,
add classifiers/URLs/keywords for PyPI page, add ollama optional dep.

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

---

## Task 2: Audit Logs — Database Schema

**Files:**
- Modify: `openraven/src/openraven/auth/db.py`
- Create: `openraven/alembic/versions/003_audit_logs.py`

- [ ] **Step 1: Add audit_logs table to db.py**

Add at the end of `openraven/src/openraven/auth/db.py` (after the `password_reset_tokens` table, before `get_engine`):

```python
audit_logs = Table(
    "audit_logs", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("user_id", String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
    Column("tenant_id", String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=True),
    Column("action", String(50), nullable=False),
    Column("details", Text, nullable=True),  # JSON string stored as Text
    Column("ip_address", String(45), nullable=True),
    Column("timestamp", DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)),
)
```

Add `Text` to the import from sqlalchemy. The current import line is:
```python
from sqlalchemy import (
    MetaData, Table, Column, String, Boolean, Integer, DateTime, ForeignKey,
    CheckConstraint, UniqueConstraint, create_engine,
)
```
Change to:
```python
from sqlalchemy import (
    MetaData, Table, Column, String, Boolean, Integer, DateTime, ForeignKey,
    CheckConstraint, UniqueConstraint, Text, create_engine,
)
```

- [ ] **Step 2: Create Alembic migration**

Create `openraven/alembic/versions/003_audit_logs.py` (note: 002 already exists for user locale):

```python
"""Audit logs table.

Revision ID: 002
Create Date: 2026-04-05
"""
from alembic import op
import sqlalchemy as sa

revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("tenant_id", sa.String(36), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=True),
        sa.Column("action", sa.String(50), nullable=False),
        sa.Column("details", sa.Text, nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_audit_tenant_timestamp", "audit_logs", ["tenant_id", sa.text("timestamp DESC")])


def downgrade() -> None:
    op.drop_index("ix_audit_tenant_timestamp", table_name="audit_logs")
    op.drop_table("audit_logs")
```

- [ ] **Step 3: Verify tables create correctly**

```bash
cd /home/ubuntu/source/OpenRaven/openraven && python3 -c "
from openraven.auth.db import get_engine, create_tables
from sqlalchemy import inspect
engine = get_engine('sqlite:///test_audit.db')
create_tables(engine)
tables = inspect(engine).get_table_names()
assert 'audit_logs' in tables, f'audit_logs not found in {tables}'
print(f'Tables: {tables}')
import os; os.remove('test_audit.db')
print('OK')
"
```
Expected: `audit_logs` in table list.

- [ ] **Step 4: Commit**

```bash
cd /home/ubuntu/source/OpenRaven && git add openraven/src/openraven/auth/db.py openraven/alembic/versions/003_audit_logs.py && git commit -m "feat(m7): add audit_logs database table and Alembic migration

New audit_logs table with user_id, tenant_id, action, details (JSON),
ip_address, timestamp. Index on (tenant_id, timestamp DESC).

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

---

## Task 3: Audit Logger Module

**Files:**
- Create: `openraven/src/openraven/audit/__init__.py`
- Create: `openraven/src/openraven/audit/logger.py`
- Create: `openraven/tests/test_audit.py`

- [ ] **Step 1: Write failing tests**

Create `openraven/tests/test_audit.py`:

```python
import json
import pytest
from sqlalchemy import select

from openraven.auth.db import audit_logs, create_tables, get_engine


@pytest.fixture
def db_engine(tmp_path):
    engine = get_engine(f"sqlite:///{tmp_path}/test_audit.db")
    create_tables(engine)
    return engine


def test_log_action_inserts_row(db_engine):
    from openraven.audit.logger import log_action
    log_action(
        engine=db_engine,
        user_id="user-1",
        tenant_id="tenant-1",
        action="login",
        details={"method": "email"},
        ip_address="127.0.0.1",
    )
    with db_engine.connect() as conn:
        rows = conn.execute(select(audit_logs)).fetchall()
    assert len(rows) == 1
    row = rows[0]
    assert row.user_id == "user-1"
    assert row.tenant_id == "tenant-1"
    assert row.action == "login"
    assert row.ip_address == "127.0.0.1"
    parsed = json.loads(row.details)
    assert parsed["method"] == "email"


def test_log_action_noop_without_engine():
    """log_action with engine=None should silently do nothing."""
    from openraven.audit.logger import log_action
    # Should not raise
    log_action(engine=None, user_id="u1", tenant_id="t1", action="login")


def test_log_action_does_not_raise_on_db_error(db_engine):
    """log_action should catch DB errors and not propagate."""
    from openraven.audit.logger import log_action
    # Close the engine's pool to simulate a DB error
    db_engine.dispose()
    # Force the underlying connection to be invalid by using a bogus engine
    from openraven.auth.db import get_engine as _ge
    bad_engine = _ge("sqlite:///nonexistent/path/db.sqlite")
    log_action(engine=bad_engine, user_id="u1", tenant_id="t1", action="login")
    # Should not raise — just log the error


def test_log_action_nullable_fields(db_engine):
    """user_id and details can be None (system events)."""
    from openraven.audit.logger import log_action
    log_action(engine=db_engine, user_id=None, tenant_id="t1", action="system_startup")
    with db_engine.connect() as conn:
        rows = conn.execute(select(audit_logs)).fetchall()
    assert len(rows) == 1
    assert rows[0].user_id is None
    assert rows[0].details is None


def test_query_audit_logs_with_filters(db_engine):
    """Query function should support action and limit filters."""
    from openraven.audit.logger import log_action, query_audit_logs
    log_action(engine=db_engine, user_id="u1", tenant_id="t1", action="login")
    log_action(engine=db_engine, user_id="u1", tenant_id="t1", action="file_ingest")
    log_action(engine=db_engine, user_id="u1", tenant_id="t1", action="login")

    all_logs = query_audit_logs(db_engine, tenant_id="t1")
    assert len(all_logs) == 3

    login_only = query_audit_logs(db_engine, tenant_id="t1", action="login")
    assert len(login_only) == 2

    limited = query_audit_logs(db_engine, tenant_id="t1", limit=2)
    assert len(limited) == 2


def test_query_audit_logs_returns_dicts(db_engine):
    """Query results should be serializable dicts."""
    from openraven.audit.logger import log_action, query_audit_logs
    log_action(engine=db_engine, user_id="u1", tenant_id="t1", action="kb_query",
               details={"question": "test?"})

    logs = query_audit_logs(db_engine, tenant_id="t1")
    assert len(logs) == 1
    log = logs[0]
    assert log["action"] == "kb_query"
    assert log["user_id"] == "u1"
    assert "timestamp" in log
    assert json.loads(log["details"])["question"] == "test?"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /home/ubuntu/source/OpenRaven/openraven && python3 -m pytest tests/test_audit.py -v 2>&1 | tail -10
```
Expected: FAIL — `openraven.audit.logger` module not found.

- [ ] **Step 3: Create audit package**

Create `openraven/src/openraven/audit/__init__.py`:
```python
```
(empty file)

Create `openraven/src/openraven/audit/logger.py`:

```python
"""Audit logging for SaaS mode (PostgreSQL-backed)."""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

from sqlalchemy import insert, select, desc
from sqlalchemy.engine import Engine

from openraven.auth.db import audit_logs

logger = logging.getLogger(__name__)


def log_action(
    engine: Engine | None,
    user_id: str | None,
    tenant_id: str | None,
    action: str,
    details: dict | None = None,
    ip_address: str = "",
) -> None:
    """Insert an audit log entry. No-op if engine is None. Never raises."""
    if engine is None:
        return
    try:
        with engine.connect() as conn:
            conn.execute(insert(audit_logs).values(
                user_id=user_id,
                tenant_id=tenant_id,
                action=action,
                details=json.dumps(details) if details else None,
                ip_address=ip_address,
                timestamp=datetime.now(timezone.utc),
            ))
            conn.commit()
    except Exception as e:
        logger.error(f"Audit log failed: {e}")


def query_audit_logs(
    engine: Engine,
    tenant_id: str,
    action: str | None = None,
    user_id: str | None = None,
    from_ts: datetime | None = None,
    to_ts: datetime | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[dict]:
    """Query audit logs with optional filters. Returns list of dicts."""
    stmt = select(audit_logs).where(audit_logs.c.tenant_id == tenant_id)

    if action:
        stmt = stmt.where(audit_logs.c.action == action)
    if user_id:
        stmt = stmt.where(audit_logs.c.user_id == user_id)
    if from_ts:
        stmt = stmt.where(audit_logs.c.timestamp >= from_ts)
    if to_ts:
        stmt = stmt.where(audit_logs.c.timestamp <= to_ts)

    stmt = stmt.order_by(desc(audit_logs.c.timestamp)).limit(limit).offset(offset)

    with engine.connect() as conn:
        rows = conn.execute(stmt).fetchall()

    return [
        {
            "id": row.id,
            "user_id": row.user_id,
            "tenant_id": row.tenant_id,
            "action": row.action,
            "details": row.details,
            "ip_address": row.ip_address,
            "timestamp": row.timestamp.isoformat() if row.timestamp else None,
        }
        for row in rows
    ]


def count_audit_logs(
    engine: Engine,
    tenant_id: str,
    action: str | None = None,
    user_id: str | None = None,
    from_ts: datetime | None = None,
    to_ts: datetime | None = None,
) -> int:
    """Count audit logs matching filters."""
    from sqlalchemy import func
    stmt = select(func.count()).select_from(audit_logs).where(audit_logs.c.tenant_id == tenant_id)
    if action:
        stmt = stmt.where(audit_logs.c.action == action)
    if user_id:
        stmt = stmt.where(audit_logs.c.user_id == user_id)
    if from_ts:
        stmt = stmt.where(audit_logs.c.timestamp >= from_ts)
    if to_ts:
        stmt = stmt.where(audit_logs.c.timestamp <= to_ts)

    with engine.connect() as conn:
        return conn.execute(stmt).scalar() or 0
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd /home/ubuntu/source/OpenRaven/openraven && python3 -m pytest tests/test_audit.py -v 2>&1 | tail -15
```
Expected: All 6 tests PASS.

- [ ] **Step 5: Commit**

```bash
cd /home/ubuntu/source/OpenRaven && git add openraven/src/openraven/audit/ openraven/tests/test_audit.py && git commit -m "feat(m7): add audit logger module with log_action and query functions

log_action() inserts audit entries, no-ops when engine is None (local
mode), never raises on DB errors. query_audit_logs() supports filters
by action, user, date range with pagination.

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

---

## Task 4: Audit API Routes

**Files:**
- Create: `openraven/src/openraven/audit/routes.py`
- Modify: `openraven/src/openraven/api/server.py`
- Modify: `openraven/tests/test_audit.py`

- [ ] **Step 1: Add API route tests**

Append to `openraven/tests/test_audit.py`:

```python
from fastapi.testclient import TestClient


@pytest.fixture
def app_with_audit(db_engine):
    """Create a FastAPI app with audit routes, mocking auth context."""
    from openraven.audit.routes import create_audit_router
    from openraven.auth.models import AuthContext
    from fastapi import FastAPI, Request
    from starlette.middleware.base import BaseHTTPMiddleware

    app = FastAPI()

    # Mock auth middleware that sets request.state.auth
    class MockAuthMiddleware(BaseHTTPMiddleware):
        async def dispatch(self, request: Request, call_next):
            request.state.auth = AuthContext(user_id="u1", tenant_id="t1", email="u1@test.com")
            return await call_next(request)

    app.add_middleware(MockAuthMiddleware)
    app.include_router(create_audit_router(db_engine), prefix="/api/audit")

    # Pre-populate some logs
    from openraven.audit.logger import log_action
    log_action(engine=db_engine, user_id="u1", tenant_id="t1", action="login", ip_address="1.2.3.4")
    log_action(engine=db_engine, user_id="u1", tenant_id="t1", action="file_ingest",
               details={"files": ["report.pdf"]})
    log_action(engine=db_engine, user_id="u2", tenant_id="t1", action="kb_query",
               details={"question": "test?"})

    return app


def test_audit_list_returns_logs(app_with_audit):
    client = TestClient(app_with_audit)
    res = client.get("/api/audit/")
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 3
    assert len(data["logs"]) == 3


def test_audit_list_filters_by_action(app_with_audit):
    client = TestClient(app_with_audit)
    res = client.get("/api/audit/?action=login")
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 1
    assert all(log["action"] == "login" for log in data["logs"])


def test_audit_list_pagination(app_with_audit):
    client = TestClient(app_with_audit)
    res = client.get("/api/audit/?limit=2&offset=0")
    assert res.status_code == 200
    data = res.json()
    assert len(data["logs"]) == 2
    assert data["total"] == 3


def test_audit_export_csv(app_with_audit):
    client = TestClient(app_with_audit)
    res = client.get("/api/audit/export")
    assert res.status_code == 200
    assert "text/csv" in res.headers["content-type"]
    lines = res.text.strip().split("\n")
    assert len(lines) == 4  # header + 3 data rows
    assert "action" in lines[0]  # CSV header
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /home/ubuntu/source/OpenRaven/openraven && python3 -m pytest tests/test_audit.py -k "audit_list or audit_export" -v 2>&1 | tail -10
```
Expected: FAIL — `openraven.audit.routes` not found.

- [ ] **Step 3: Create audit routes**

Create `openraven/src/openraven/audit/routes.py`:

```python
"""Audit log API routes."""
from __future__ import annotations

import csv
import io
from datetime import datetime

from fastapi import APIRouter, Query, Request, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.engine import Engine

from openraven.audit.logger import query_audit_logs, count_audit_logs


def _sanitize_csv_cell(value: str) -> str:
    """Prevent CSV formula injection (OWASP)."""
    if value and value[0] in ("=", "+", "-", "@", "\t", "\r"):
        return "'" + value
    return value


def create_audit_router(engine: Engine) -> APIRouter:
    router = APIRouter()

    def _get_tenant_id(request: Request) -> str:
        """Extract tenant_id from auth context. Raises 401 if not authenticated."""
        auth = getattr(request.state, "auth", None)
        if not auth:
            raise HTTPException(401, "Not authenticated")
        return auth.tenant_id

    @router.get("/")
    async def list_audit_logs(
        request: Request,
        action: str | None = Query(default=None),
        user_id: str | None = Query(default=None),
        from_date: str | None = Query(default=None, alias="from"),
        to_date: str | None = Query(default=None, alias="to"),
        limit: int = Query(default=100, ge=1, le=1000),
        offset: int = Query(default=0, ge=0),
    ):
        tenant_id = _get_tenant_id(request)
        from_ts = datetime.fromisoformat(from_date) if from_date else None
        to_ts = datetime.fromisoformat(to_date) if to_date else None

        logs = query_audit_logs(
            engine, tenant_id=tenant_id, action=action, user_id=user_id,
            from_ts=from_ts, to_ts=to_ts, limit=limit, offset=offset,
        )
        total = count_audit_logs(
            engine, tenant_id=tenant_id, action=action, user_id=user_id,
            from_ts=from_ts, to_ts=to_ts,
        )
        return {"logs": logs, "total": total, "limit": limit, "offset": offset}

    @router.get("/export")
    async def export_audit_logs(
        request: Request,
        action: str | None = Query(default=None),
        user_id: str | None = Query(default=None),
        from_date: str | None = Query(default=None, alias="from"),
        to_date: str | None = Query(default=None, alias="to"),
    ):
        tenant_id = _get_tenant_id(request)
        from_ts = datetime.fromisoformat(from_date) if from_date else None
        to_ts = datetime.fromisoformat(to_date) if to_date else None

        logs = query_audit_logs(
            engine, tenant_id=tenant_id, action=action, user_id=user_id,
            from_ts=from_ts, to_ts=to_ts, limit=10000, offset=0,
        )

        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=["timestamp", "user_id", "action", "details", "ip_address"])
        writer.writeheader()
        for log in logs:
            writer.writerow({
                "timestamp": _sanitize_csv_cell(log["timestamp"] or ""),
                "user_id": _sanitize_csv_cell(log["user_id"] or ""),
                "action": _sanitize_csv_cell(log["action"]),
                "details": _sanitize_csv_cell(log["details"] or ""),
                "ip_address": _sanitize_csv_cell(log["ip_address"] or ""),
            })

        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=audit_logs.csv"},
        )

    return router
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd /home/ubuntu/source/OpenRaven/openraven && python3 -m pytest tests/test_audit.py -v 2>&1 | tail -15
```
Expected: All 10 tests PASS.

- [ ] **Step 5: Commit**

```bash
cd /home/ubuntu/source/OpenRaven && git add openraven/src/openraven/audit/routes.py openraven/tests/test_audit.py && git commit -m "feat(m7): add audit log API routes (list + CSV export)

GET /api/audit with filters (action, user, date range, pagination).
GET /api/audit/export returns CSV download.

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

---

## Task 5: Wire Audit Logging into Server and Auth Routes

**Files:**
- Modify: `openraven/src/openraven/api/server.py`
- Modify: `openraven/src/openraven/auth/routes.py`

- [ ] **Step 1: Register audit routes in server.py**

In `openraven/src/openraven/api/server.py`, inside the `if config.auth_enabled:` block (around line 115-125), after the auth router is included, add:

```python
        from openraven.audit.routes import create_audit_router
        app.include_router(create_audit_router(auth_engine), prefix="/api/audit", tags=["audit"])
```

- [ ] **Step 2: Add log_action helper to server.py**

After the `resolve_pipeline` function definition (around line 164), add a helper:

```python
    def _audit(request: Request, action: str, details: dict | None = None) -> None:
        """Log an audit event if auth is enabled."""
        if not config.auth_enabled or not auth_engine:
            return
        from openraven.audit.logger import log_action
        auth_ctx = getattr(request.state, "auth", None)
        log_action(
            engine=auth_engine,
            user_id=auth_ctx.user_id if auth_ctx else None,
            tenant_id=auth_ctx.tenant_id if auth_ctx else None,
            action=action,
            details=details,
            ip_address=request.client.host if request.client else "",
        )
```

- [ ] **Step 3: Add audit calls to key endpoints in server.py**

In the **ingest** endpoint (around line 245, after `return IngestResponse(...)`), add before the return:

```python
        _audit(request, "file_ingest", {
            "files": [Path(upload.filename).name for upload in files if upload.filename],
            "files_processed": result.files_processed,
            "entities_extracted": result.entities_extracted,
        })
```

Note: the ingest function signature needs `request: Request` added. Change:
```python
    async def ingest(files: list[UploadFile] = File(...), schema: str | None = Form(default=None)):
```
to:
```python
    async def ingest(request: Request, files: list[UploadFile] = File(...), schema: str | None = Form(default=None)):
```

In the **ask** endpoint (`async def ask` at line 189), add `request: Request` to the signature and an audit call. Change:
```python
    async def ask(req: AskRequest):
```
to:
```python
    async def ask(request: Request, req: AskRequest):
```
Then add before the return statement:
```python
        _audit(request, "kb_query", {"question": req.question[:200], "mode": req.mode})
```

- [ ] **Step 4: Add audit calls to auth routes**

In `openraven/src/openraven/auth/routes.py`, the `create_auth_router` function creates an `APIRouter`. We need to add audit logging to login, signup, logout, and password reset.

At the top of the `create_auth_router` function body, add:

```python
    def _audit_auth(request: Request, action: str, user_id: str | None = None, details: dict | None = None):
        from openraven.audit.logger import log_action
        ip = request.client.host if request.client else ""
        log_action(engine=engine, user_id=user_id, tenant_id=None, action=action, details=details, ip_address=ip)
```

Then add calls at the end of each handler (before the return). The actual variable names in the codebase:

- **login** handler (`async def login(data: UserLogin, request: Request, response: Response)`):
  Insert before the return at line 125:
  `_audit_auth(request, "login", user_id=row.id, details={"email": data.email})`

- **signup** handler (`async def signup(data: UserCreate, request: Request, response: Response)`):
  Insert before the return. The handler creates `user_id = str(uuid.uuid4())`:
  `_audit_auth(request, "signup", user_id=user_id, details={"email": data.email})`

- **logout** handler (`async def logout(request: Request, response: Response)`):
  This handler has no auth context (just deletes the cookie). Extract session_id before deletion:
  ```python
  session_id = request.cookies.get("session_id")
  if session_id:
      from openraven.auth.sessions import validate_session
      _ctx = validate_session(engine, session_id)
      _audit_auth(request, "logout", user_id=_ctx.user_id if _ctx else None)
      delete_session(engine, session_id)
  ```
  This replaces the existing `if session_id: delete_session(engine, session_id)` block.

- **reset-password** POST handler:
  `_audit_auth(request, "password_reset", details={"email": data.email})`

- [ ] **Step 5: Run all tests**

```bash
cd /home/ubuntu/source/OpenRaven/openraven && python3 -m pytest tests/test_audit.py tests/test_auth.py tests/test_api.py -v 2>&1 | tail -20
```
Expected: All tests PASS.

- [ ] **Step 6: Commit**

```bash
cd /home/ubuntu/source/OpenRaven && git add openraven/src/openraven/api/server.py openraven/src/openraven/auth/routes.py && git commit -m "feat(m7): wire audit logging into server and auth endpoints

Audit events logged for: login, signup, logout, password_reset,
file_ingest, kb_query. Audit routes registered at /api/audit.
All logging is no-op in local mode (no DATABASE_URL).

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

---

## Task 6: Audit Log UI Page

**Files:**
- Create: `openraven-ui/src/pages/AuditLogPage.tsx`
- Modify: `openraven-ui/src/App.tsx`

- [ ] **Step 1: Read App.tsx to understand routing pattern**

Read `openraven-ui/src/App.tsx` to see how routes are defined and where to add the new `/audit` route.

- [ ] **Step 2: Create AuditLogPage component**

Create `openraven-ui/src/pages/AuditLogPage.tsx`:

```tsx
import { useEffect, useState } from "react";

interface AuditLog {
  id: number;
  user_id: string | null;
  action: string;
  details: string | null;
  ip_address: string | null;
  timestamp: string | null;
}

interface AuditResponse {
  logs: AuditLog[];
  total: number;
  limit: number;
  offset: number;
}

const ACTION_OPTIONS = [
  "", "login", "logout", "signup", "password_reset",
  "file_ingest", "kb_query", "agent_deploy", "agent_undeploy",
];

export default function AuditLogPage() {
  const [data, setData] = useState<AuditResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [action, setAction] = useState("");
  const [page, setPage] = useState(0);
  const limit = 50;

  useEffect(() => {
    setLoading(true);
    const params = new URLSearchParams({ limit: String(limit), offset: String(page * limit) });
    if (action) params.set("action", action);

    fetch(`/api/audit?${params}`)
      .then(r => r.json())
      .then(setData)
      .catch(() => setData(null))
      .finally(() => setLoading(false));
  }, [action, page]);

  function handleExport() {
    const params = new URLSearchParams();
    if (action) params.set("action", action);
    window.open(`/api/audit/export?${params}`, "_blank");
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-3xl" style={{ color: "var(--color-text)", lineHeight: 1.15 }}>Audit Log</h1>
        <button
          onClick={handleExport}
          className="px-4 py-2 text-sm cursor-pointer"
          style={{ background: "var(--color-dark)", color: "var(--color-text-on-brand)" }}
        >
          EXPORT CSV
        </button>
      </div>

      <div className="flex gap-4 mb-6">
        <div>
          <label htmlFor="action-filter" className="block text-xs mb-1" style={{ color: "var(--color-text-muted)" }}>Action</label>
          <select
            id="action-filter"
            value={action}
            onChange={e => { setAction(e.target.value); setPage(0); }}
            className="px-3 py-2 text-sm cursor-pointer"
            style={{ background: "var(--bg-surface)", border: "1px solid var(--color-border)", color: "var(--color-text)" }}
          >
            <option value="">All actions</option>
            {ACTION_OPTIONS.filter(Boolean).map(a => <option key={a} value={a}>{a}</option>)}
          </select>
        </div>
      </div>

      {loading && (
        <div className="text-sm animate-pulse" style={{ color: "var(--color-text-muted)" }}>Loading...</div>
      )}

      {data && !loading && (
        <>
          <div className="overflow-x-auto">
            <table className="w-full text-sm" style={{ borderCollapse: "collapse" }}>
              <thead>
                <tr style={{ borderBottom: "2px solid var(--color-border)" }}>
                  {["Timestamp", "User", "Action", "Details", "IP"].map(h => (
                    <th key={h} className="text-left py-2 px-3 text-xs uppercase" style={{ color: "var(--color-text-muted)" }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {data.logs.map(log => (
                  <tr key={log.id} style={{ borderBottom: "1px solid var(--color-border)" }}>
                    <td className="py-2 px-3 text-xs" style={{ color: "var(--color-text-secondary)" }}>
                      {log.timestamp ? new Date(log.timestamp).toLocaleString() : "—"}
                    </td>
                    <td className="py-2 px-3 text-xs" style={{ color: "var(--color-text)" }}>{log.user_id ?? "system"}</td>
                    <td className="py-2 px-3">
                      <span className="text-xs px-2 py-0.5" style={{ background: "var(--bg-surface)", color: "var(--color-text)" }}>
                        {log.action}
                      </span>
                    </td>
                    <td className="py-2 px-3 text-xs max-w-xs truncate" style={{ color: "var(--color-text-muted)" }}>
                      {log.details ?? "—"}
                    </td>
                    <td className="py-2 px-3 text-xs" style={{ color: "var(--color-text-muted)" }}>{log.ip_address ?? "—"}</td>
                  </tr>
                ))}
                {data.logs.length === 0 && (
                  <tr><td colSpan={5} className="py-8 text-center text-sm" style={{ color: "var(--color-text-muted)" }}>No audit logs found.</td></tr>
                )}
              </tbody>
            </table>
          </div>

          <div className="flex items-center justify-between mt-4">
            <span className="text-xs" style={{ color: "var(--color-text-muted)" }}>
              Showing {data.offset + 1}–{Math.min(data.offset + data.logs.length, data.total)} of {data.total}
            </span>
            <div className="flex gap-2">
              <button
                onClick={() => setPage(p => Math.max(0, p - 1))}
                disabled={page === 0}
                className="px-3 py-1 text-xs cursor-pointer disabled:opacity-50 disabled:cursor-default"
                style={{ background: "var(--bg-surface)", border: "1px solid var(--color-border)", color: "var(--color-text)" }}
              >Prev</button>
              <button
                onClick={() => setPage(p => p + 1)}
                disabled={data.offset + data.logs.length >= data.total}
                className="px-3 py-1 text-xs cursor-pointer disabled:opacity-50 disabled:cursor-default"
                style={{ background: "var(--bg-surface)", border: "1px solid var(--color-border)", color: "var(--color-text)" }}
              >Next</button>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
```

- [ ] **Step 3: Add /audit route to App.tsx**

Read `openraven-ui/src/App.tsx` to find where routes are defined. Add a new route for `/audit` pointing to `AuditLogPage`. Also add a nav link (visible only if you want — the spec says admin-only, but for now we'll add the route and the link).

Import at top:
```tsx
import AuditLogPage from "./pages/AuditLogPage";
```

Add route alongside existing routes:
```tsx
<Route path="/audit" element={<AuditLogPage />} />
```

Add nav link alongside existing nav links:
```tsx
<NavLink to="/audit">Audit</NavLink>
```

- [ ] **Step 4: Verify UI builds**

```bash
cd /home/ubuntu/source/OpenRaven/openraven-ui && bun run build 2>&1 | tail -5
```
Expected: Build succeeds.

- [ ] **Step 5: Commit**

```bash
cd /home/ubuntu/source/OpenRaven && git add openraven-ui/src/pages/AuditLogPage.tsx openraven-ui/src/App.tsx && git commit -m "feat(m7): add audit log UI page with table, filters, pagination, CSV export

AuditLogPage at /audit shows timestamped action log with action filter,
pagination, and CSV export button. Styled with Mistral Premium tokens.

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

---

## Task 7: Add Audit BFF Proxy Route

**Files:**
- Modify: `openraven-ui/server/index.ts`

- [ ] **Step 1: Add audit proxy using existing `proxyToCore` pattern**

In `openraven-ui/server/index.ts`, add these lines after the existing `app.get("/api/schemas", ...)` block (around line 88). Follow the exact pattern used by `/api/connectors/*`, `/api/agents/*`, etc.:

```typescript
// Audit log proxy with binary passthrough for CSV export
app.all("/api/audit/*", async (c) => {
  try {
    if (c.req.path.endsWith("/export")) {
      const url = `${CORE_API_URL}${c.req.path}${c.req.url.includes("?") ? "?" + c.req.url.split("?")[1] : ""}`;
      const res = await fetch(url, {
        method: c.req.method,
        headers: { Cookie: c.req.header("Cookie") ?? "" },
      });
      return new Response(res.body, {
        status: res.status,
        headers: {
          "content-type": res.headers.get("content-type") || "text/csv",
          "content-disposition": res.headers.get("content-disposition") || "attachment; filename=audit_logs.csv",
        },
      });
    }
    return await proxyToCore(c);
  } catch (e) { return c.json({ error: `Core engine error: ${(e as Error).message}` }, 502); }
});
app.all("/api/audit", async (c) => {
  try { return await proxyToCore(c); }
  catch (e) { return c.json({ error: `Core engine error: ${(e as Error).message}` }, 502); }
});
```

No separate route file needed — this follows the exact pattern of every other proxy route in `index.ts`.

- [ ] **Step 2: Verify UI builds**

```bash
cd /home/ubuntu/source/OpenRaven/openraven-ui && bun run build 2>&1 | tail -5
```
Expected: Build succeeds.

- [ ] **Step 3: Commit**

```bash
cd /home/ubuntu/source/OpenRaven && git add openraven-ui/server/index.ts && git commit -m "feat(m7): add BFF proxy for audit log API using existing proxyToCore

Forwards /api/audit and /api/audit/export to core API. CSV export
uses binary passthrough for correct content-type.

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

---

## Task 8: Final Integration Test

**Files:** None (verification only)

- [ ] **Step 1: Run all Python tests**

```bash
cd /home/ubuntu/source/OpenRaven/openraven && python3 -m pytest tests/ -v --ignore=tests/benchmark --ignore=tests/fixtures 2>&1 | tail -30
```
Expected: All tests pass (existing + new audit tests).

- [ ] **Step 2: Run UI build**

```bash
cd /home/ubuntu/source/OpenRaven/openraven-ui && bun run build 2>&1 | tail -5
```
Expected: Build succeeds.

- [ ] **Step 3: Verify package still builds**

```bash
cd /home/ubuntu/source/OpenRaven/openraven && python3 -m build 2>&1 | tail -5
```
Expected: Build succeeds.
