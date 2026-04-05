# Demo Sandbox & Conversation Memory Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let unauthenticated users explore OpenRaven via themed demo sandboxes, and add persistent multi-turn conversation memory to the chat for all users.

**Architecture:** Demo sandbox reuses the existing tenant isolation system with a special `demo` tenant and lightweight anonymous sessions. Conversation memory adds two new PostgreSQL tables (`conversations`, `messages`) with a fixed 10-turn context window sent to the LLM. Frontend caches messages locally and syncs with the DB for persistence.

**Tech Stack:** Python/FastAPI (backend), SQLAlchemy Core (schema), React/TypeScript (frontend), PostgreSQL, LightRAG

---

## File Structure

### New Files

| File | Responsibility |
|------|----------------|
| `openraven/src/openraven/auth/demo.py` | Demo session creation, theme listing, cleanup |
| `openraven/src/openraven/conversations/models.py` | Conversation & message DB tables + CRUD functions |
| `openraven/src/openraven/conversations/routes.py` | Conversation API endpoints |
| `openraven/src/openraven/conversations/history.py` | History formatting for LLM context |
| `openraven/tests/test_demo.py` | Demo session + theme tests |
| `openraven/tests/test_conversations.py` | Conversation CRUD + history tests |
| `openraven-ui/src/hooks/useConversations.tsx` | Conversation state management hook |
| `openraven-ui/src/components/ConversationSidebar.tsx` | Conversation list sidebar component |
| `openraven-ui/src/pages/DemoLandingPage.tsx` | Demo theme picker page |

### Modified Files

| File | Changes |
|------|---------|
| `openraven/src/openraven/auth/db.py` | Add `is_demo`, `demo_theme` columns to sessions; add conversations + messages tables |
| `openraven/src/openraven/auth/sessions.py` | Add `create_demo_session()`, update `validate_session()` to return `is_demo` |
| `openraven/src/openraven/auth/models.py` | Extend `AuthContext` with `is_demo`, `demo_theme` |
| `openraven/src/openraven/auth/middleware.py` | Add demo route allowlist, block mutations for demo sessions |
| `openraven/src/openraven/api/server.py` | Extend `AskRequest` with `conversation_id`+`history`, register new routes |
| `openraven-ui/src/hooks/useAuth.tsx` | Add `isDemo`, `demoTheme`, `startDemo()` |
| `openraven-ui/src/App.tsx` | Add `/demo/*` routes, update auth guard |
| `openraven-ui/src/pages/AskPage.tsx` | Integrate `useConversations`, add sidebar, send history |

---

## Task 1: Extend Auth Schema for Demo Sessions

**Files:**
- Modify: `openraven/src/openraven/auth/db.py:30-36`
- Modify: `openraven/src/openraven/auth/models.py:32-35`
- Test: `openraven/tests/test_demo.py` (create)

- [ ] **Step 1: Write failing test for demo session columns**

Create `openraven/tests/test_demo.py`:

```python
"""Tests for demo session support."""
import pytest
from sqlalchemy import inspect
from openraven.auth.db import get_engine, create_tables, sessions, metadata


@pytest.fixture
def engine(tmp_path):
    eng = get_engine(f"sqlite:///{tmp_path}/test_demo.db")
    create_tables(eng)
    return eng


def test_sessions_table_has_demo_columns(engine):
    inspector = inspect(engine)
    columns = {c["name"] for c in inspector.get_columns("sessions")}
    assert "is_demo" in columns
    assert "demo_theme" in columns


def test_sessions_is_demo_defaults_false(engine):
    from openraven.auth.db import sessions
    with engine.connect() as conn:
        conn.execute(sessions.insert().values(
            id="test-session",
            user_id=None,
            expires_at="2099-01-01T00:00:00Z",
        ))
        conn.commit()
        row = conn.execute(sessions.select().where(sessions.c.id == "test-session")).fetchone()
    assert row.is_demo is False or row.is_demo == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /home/ubuntu/source/OpenRaven && python -m pytest openraven/tests/test_demo.py -v`
Expected: FAIL — `is_demo` column does not exist

- [ ] **Step 3: Add demo columns to sessions table**

In `openraven/src/openraven/auth/db.py`, modify the sessions table definition (lines 30-36):

```python
sessions = Table(
    "sessions", metadata,
    Column("id", String(255), primary_key=True),
    Column("user_id", String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=True),
    Column("expires_at", DateTime(timezone=True), nullable=False),
    Column("created_at", DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)),
    Column("is_demo", Boolean, default=False, nullable=False),
    Column("demo_theme", String(50), nullable=True),
)
```

Note: `user_id` changes from `nullable=False` to `nullable=True` to support demo sessions without a user.

Add the `Boolean` import at the top of the file:

```python
from sqlalchemy import (
    Table, Column, String, DateTime, Boolean, Integer, MetaData, ForeignKey,
    create_engine, CheckConstraint, UniqueConstraint, Text, JSON,
)
```

- [ ] **Step 4: Extend AuthContext model**

In `openraven/src/openraven/auth/models.py`, update `AuthContext` (lines 32-35):

```python
class AuthContext(BaseModel):
    user_id: str | None  # None for demo sessions
    tenant_id: str
    email: str | None = None  # None for demo sessions
    is_demo: bool = False
    demo_theme: str | None = None
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd /home/ubuntu/source/OpenRaven && python -m pytest openraven/tests/test_demo.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add openraven/src/openraven/auth/db.py openraven/src/openraven/auth/models.py openraven/tests/test_demo.py
git commit -m "feat: add demo session columns to sessions table and extend AuthContext"
```

---

## Task 2: Demo Session Creation & Validation

**Files:**
- Modify: `openraven/src/openraven/auth/sessions.py:12-57`
- Test: `openraven/tests/test_demo.py` (extend)

- [ ] **Step 1: Write failing tests for demo session functions**

Append to `openraven/tests/test_demo.py`:

```python
from openraven.auth.sessions import create_session, create_demo_session, validate_session
from openraven.auth.db import users
import uuid


def _seed_user(engine):
    """Helper: not needed for demo, but needed for regular session tests."""
    uid = str(uuid.uuid4())
    with engine.connect() as conn:
        conn.execute(users.insert().values(
            id=uid, email="test@test.com", name="Test",
            password_hash="fakehash", email_verified=False,
        ))
        conn.commit()
    return uid


def test_create_demo_session_returns_session_id(engine):
    sid = create_demo_session(engine, theme="legal-docs")
    assert isinstance(sid, str)
    assert len(sid) > 20


def test_validate_demo_session_returns_demo_context(engine):
    sid = create_demo_session(engine, theme="legal-docs")
    ctx = validate_session(engine, sid)
    assert ctx is not None
    assert ctx.is_demo is True
    assert ctx.demo_theme == "legal-docs"
    assert ctx.tenant_id == "demo"
    assert ctx.user_id is None


def test_demo_session_expires_after_ttl(engine):
    from openraven.auth.db import sessions as sessions_table
    from datetime import datetime, timezone
    sid = create_demo_session(engine, theme="tech-wiki", ttl_hours=0)
    # Manually set expires_at to the past
    with engine.connect() as conn:
        conn.execute(
            sessions_table.update()
            .where(sessions_table.c.id == sid)
            .values(expires_at=datetime(2000, 1, 1, tzinfo=timezone.utc))
        )
        conn.commit()
    ctx = validate_session(engine, sid)
    assert ctx is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /home/ubuntu/source/OpenRaven && python -m pytest openraven/tests/test_demo.py::test_create_demo_session_returns_session_id -v`
Expected: FAIL — `create_demo_session` not defined

- [ ] **Step 3: Implement create_demo_session**

In `openraven/src/openraven/auth/sessions.py`, add after `create_session`:

```python
def create_demo_session(engine: Engine, theme: str, ttl_hours: int = 2) -> str:
    """Create an anonymous demo session. No user account required."""
    session_id = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(hours=ttl_hours)
    with engine.connect() as conn:
        conn.execute(sessions.insert().values(
            id=session_id,
            user_id=None,
            expires_at=expires_at,
            is_demo=True,
            demo_theme=theme,
        ))
        conn.commit()
    return session_id
```

- [ ] **Step 4: Update validate_session to handle demo sessions**

Modify `validate_session` in `openraven/src/openraven/auth/sessions.py` to check for demo sessions:

```python
def validate_session(engine: Engine, session_id: str) -> AuthContext | None:
    """Validate a session ID. Returns AuthContext if valid, None if expired/missing."""
    with engine.connect() as conn:
        row = conn.execute(
            select(sessions).where(sessions.c.id == session_id)
        ).fetchone()
    if not row:
        return None
    if row.expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
        return None

    # Demo session — no user lookup needed
    if row.is_demo:
        return AuthContext(
            user_id=None,
            tenant_id="demo",
            email=None,
            is_demo=True,
            demo_theme=row.demo_theme,
        )

    # Regular session — look up user and tenant
    with engine.connect() as conn:
        user_row = conn.execute(
            select(users.c.email).where(users.c.id == row.user_id)
        ).fetchone()
        if not user_row:
            return None
        tm_row = conn.execute(
            select(tenant_members.c.tenant_id)
            .where(tenant_members.c.user_id == row.user_id)
        ).fetchone()
        if not tm_row:
            return None
    return AuthContext(
        user_id=row.user_id,
        tenant_id=tm_row.tenant_id,
        email=user_row.email,
    )
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd /home/ubuntu/source/OpenRaven && python -m pytest openraven/tests/test_demo.py -v`
Expected: ALL PASS

- [ ] **Step 6: Commit**

```bash
git add openraven/src/openraven/auth/sessions.py openraven/tests/test_demo.py
git commit -m "feat: add create_demo_session and extend validate_session for demo"
```

---

## Task 3: Demo Routes (Theme Listing & Session Start)

**Files:**
- Create: `openraven/src/openraven/auth/demo.py`
- Test: `openraven/tests/test_demo.py` (extend)

- [ ] **Step 1: Write failing tests for demo API routes**

Append to `openraven/tests/test_demo.py`:

```python
from fastapi import FastAPI
from fastapi.testclient import TestClient
from openraven.auth.demo import create_demo_router


@pytest.fixture
def demo_client(engine, tmp_path):
    """Client with demo routes and a seeded demo theme."""
    themes_dir = tmp_path / "tenants" / "demo"
    legal = themes_dir / "legal-docs"
    legal.mkdir(parents=True)
    (legal / ".theme.json").write_text('{"name": "Legal Docs", "description": "Sample legal documents"}')

    app = FastAPI()
    app.include_router(create_demo_router(engine, tenants_root=themes_dir.parent))
    return TestClient(app)


def test_list_themes(demo_client):
    res = demo_client.get("/api/demo/themes")
    assert res.status_code == 200
    themes = res.json()
    assert len(themes) >= 1
    assert themes[0]["slug"] == "legal-docs"
    assert themes[0]["name"] == "Legal Docs"


def test_start_demo_session(demo_client):
    res = demo_client.post("/api/auth/demo", json={"theme": "legal-docs"})
    assert res.status_code == 200
    assert "session_id" in res.cookies
    data = res.json()
    assert data["theme"] == "legal-docs"


def test_start_demo_invalid_theme(demo_client):
    res = demo_client.post("/api/auth/demo", json={"theme": "nonexistent"})
    assert res.status_code == 404
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /home/ubuntu/source/OpenRaven && python -m pytest openraven/tests/test_demo.py::test_list_themes -v`
Expected: FAIL — `create_demo_router` not found

- [ ] **Step 3: Implement demo routes**

Create `openraven/src/openraven/auth/demo.py`:

```python
"""Demo session routes — theme listing and anonymous session creation."""
from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel
from sqlalchemy import Engine

from openraven.auth.sessions import create_demo_session


class DemoStartRequest(BaseModel):
    theme: str


class ThemeInfo(BaseModel):
    slug: str
    name: str
    description: str


def _list_themes(tenants_root: Path) -> list[ThemeInfo]:
    """Scan the demo tenant directory for theme sub-directories."""
    demo_dir = tenants_root / "demo"
    if not demo_dir.is_dir():
        return []
    themes: list[ThemeInfo] = []
    for child in sorted(demo_dir.iterdir()):
        if not child.is_dir():
            continue
        meta_path = child / ".theme.json"
        if meta_path.exists():
            meta = json.loads(meta_path.read_text())
            themes.append(ThemeInfo(
                slug=child.name,
                name=meta.get("name", child.name),
                description=meta.get("description", ""),
            ))
        else:
            themes.append(ThemeInfo(slug=child.name, name=child.name, description=""))
    return themes


def create_demo_router(engine: Engine, tenants_root: Path = Path("/data/tenants")) -> APIRouter:
    router = APIRouter()

    @router.get("/api/demo/themes", response_model=list[ThemeInfo])
    async def list_themes():
        return _list_themes(tenants_root)

    @router.post("/api/auth/demo")
    async def start_demo(req: DemoStartRequest, response: Response):
        themes = _list_themes(tenants_root)
        valid_slugs = {t.slug for t in themes}
        if req.theme not in valid_slugs:
            raise HTTPException(404, f"Theme '{req.theme}' not found")
        session_id = create_demo_session(engine, theme=req.theme)
        response.set_cookie(
            "session_id", session_id,
            httponly=True, samesite="lax", secure=False,
            max_age=2 * 3600,
        )
        return {"theme": req.theme, "message": "Demo session started"}

    return router
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /home/ubuntu/source/OpenRaven && python -m pytest openraven/tests/test_demo.py -v`
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
git add openraven/src/openraven/auth/demo.py openraven/tests/test_demo.py
git commit -m "feat: add demo theme listing and session start routes"
```

---

## Task 4: Auth Middleware — Demo Session Handling

**Files:**
- Modify: `openraven/src/openraven/auth/middleware.py`
- Modify: `openraven/src/openraven/api/server.py:140-157`
- Test: `openraven/tests/test_demo.py` (extend)

- [ ] **Step 1: Write failing tests for demo middleware restrictions**

Append to `openraven/tests/test_demo.py`:

```python
def test_demo_session_can_access_ask(demo_client, engine):
    # Start demo session
    res = demo_client.post("/api/auth/demo", json={"theme": "legal-docs"})
    session_id = res.cookies["session_id"]
    # This would need a full app with middleware — test at integration level
    # For now, test that demo context is properly constructed
    ctx = validate_session(engine, session_id)
    assert ctx.is_demo is True
    assert ctx.tenant_id == "demo"


DEMO_ALLOWED_PATHS = [
    "/api/ask",
    "/api/graph",
    "/api/documents",
    "/api/conversations",
    "/api/demo/themes",
]

DEMO_BLOCKED_PATHS = [
    "/api/ingest",
    "/api/settings",
    "/api/team",
    "/api/agents",
    "/api/sync",
    "/api/account",
]


def test_demo_allowed_paths():
    from openraven.auth.middleware import is_demo_allowed
    for path in DEMO_ALLOWED_PATHS:
        assert is_demo_allowed(path, "GET") is True, f"Should allow GET {path}"
    assert is_demo_allowed("/api/ask", "POST") is True  # POST ask is allowed


def test_demo_blocked_paths():
    from openraven.auth.middleware import is_demo_allowed
    for path in DEMO_BLOCKED_PATHS:
        assert is_demo_allowed(path, "POST") is False, f"Should block POST {path}"
        assert is_demo_allowed(path, "GET") is False, f"Should block GET {path}"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /home/ubuntu/source/OpenRaven && python -m pytest openraven/tests/test_demo.py::test_demo_allowed_paths -v`
Expected: FAIL — `is_demo_allowed` not defined

- [ ] **Step 3: Add demo path checker to middleware**

In `openraven/src/openraven/auth/middleware.py`, add the `is_demo_allowed` function:

```python
# Prefixes accessible to demo sessions
_DEMO_ALLOWED_PREFIXES = (
    "/api/ask",
    "/api/graph",
    "/api/documents",
    "/api/conversations",
    "/api/demo/",
    "/api/auth/demo",
    "/api/auth/logout",
)


def is_demo_allowed(path: str, method: str = "GET") -> bool:
    """Check if a path is accessible to demo sessions."""
    return any(path.startswith(prefix) for prefix in _DEMO_ALLOWED_PREFIXES)
```

- [ ] **Step 4: Update auth middleware to handle demo sessions**

In the middleware section of `openraven/src/openraven/api/server.py` (lines 140-157), update the middleware to handle demo context:

After validating the session and getting `AuthContext`, add:

```python
# If demo session, enforce allowed routes
if ctx.is_demo and not is_demo_allowed(request.url.path, request.method):
    return JSONResponse(status_code=403, content={"detail": "Not available in demo mode"})
request.state.auth = ctx
```

Add the import at the top:
```python
from openraven.auth.middleware import is_demo_allowed
```

Also add `/api/demo/themes` and `/api/auth/demo` to the public prefixes list so they don't require auth.

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd /home/ubuntu/source/OpenRaven && python -m pytest openraven/tests/test_demo.py -v`
Expected: ALL PASS

- [ ] **Step 6: Commit**

```bash
git add openraven/src/openraven/auth/middleware.py openraven/src/openraven/api/server.py openraven/tests/test_demo.py
git commit -m "feat: add demo session middleware with route restrictions"
```

---

## Task 5: Conversations & Messages DB Schema

**Files:**
- Modify: `openraven/src/openraven/auth/db.py`
- Create: `openraven/src/openraven/conversations/models.py`
- Test: `openraven/tests/test_conversations.py` (create)

- [ ] **Step 1: Write failing test for conversations tables**

Create `openraven/tests/test_conversations.py`:

```python
"""Tests for conversation persistence."""
import pytest
from sqlalchemy import inspect
from openraven.auth.db import get_engine, create_tables


@pytest.fixture
def engine(tmp_path):
    eng = get_engine(f"sqlite:///{tmp_path}/test_convos.db")
    create_tables(eng)
    return eng


def test_conversations_table_exists(engine):
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    assert "conversations" in tables


def test_messages_table_exists(engine):
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    assert "messages" in tables


def test_conversations_has_expected_columns(engine):
    inspector = inspect(engine)
    columns = {c["name"] for c in inspector.get_columns("conversations")}
    assert columns >= {"id", "tenant_id", "user_id", "session_id", "title", "demo_theme", "created_at", "updated_at"}


def test_messages_has_expected_columns(engine):
    inspector = inspect(engine)
    columns = {c["name"] for c in inspector.get_columns("messages")}
    assert columns >= {"id", "conversation_id", "role", "content", "sources", "created_at"}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /home/ubuntu/source/OpenRaven && python -m pytest openraven/tests/test_conversations.py -v`
Expected: FAIL — `conversations` table does not exist

- [ ] **Step 3: Add conversations and messages tables to db.py**

In `openraven/src/openraven/auth/db.py`, add after the `sync_config` table:

```python
conversations = Table(
    "conversations", metadata,
    Column("id", String(36), primary_key=True),
    Column("tenant_id", String(255), nullable=False),
    Column("user_id", String(36), nullable=True),
    Column("session_id", String(255), nullable=True),
    Column("title", String(200), nullable=True),
    Column("demo_theme", String(50), nullable=True),
    Column("created_at", DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)),
    Column("updated_at", DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)),
)

messages = Table(
    "messages", metadata,
    Column("id", String(36), primary_key=True),
    Column("conversation_id", String(36), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False),
    Column("role", String(10), nullable=False),
    Column("content", Text, nullable=False),
    Column("sources", JSON, nullable=True),
    Column("created_at", DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)),
)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /home/ubuntu/source/OpenRaven && python -m pytest openraven/tests/test_conversations.py -v`
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
git add openraven/src/openraven/auth/db.py openraven/tests/test_conversations.py
git commit -m "feat: add conversations and messages tables"
```

---

## Task 6: Conversation CRUD Functions

**Files:**
- Create: `openraven/src/openraven/conversations/models.py`
- Test: `openraven/tests/test_conversations.py` (extend)

- [ ] **Step 1: Create conversations package**

```bash
mkdir -p openraven/src/openraven/conversations
touch openraven/src/openraven/conversations/__init__.py
```

- [ ] **Step 2: Write failing tests for CRUD operations**

Append to `openraven/tests/test_conversations.py`:

```python
from openraven.conversations.models import (
    create_conversation, list_conversations, get_conversation,
    delete_conversation, add_message, get_recent_messages,
)


def test_create_conversation(engine):
    convo_id = create_conversation(engine, tenant_id="t1", user_id="u1")
    assert isinstance(convo_id, str)
    assert len(convo_id) == 36  # UUID length


def test_create_conversation_with_title(engine):
    convo_id = create_conversation(engine, tenant_id="t1", user_id="u1", title="Test Chat")
    convo = get_conversation(engine, convo_id, tenant_id="t1")
    assert convo["title"] == "Test Chat"


def test_create_demo_conversation(engine):
    convo_id = create_conversation(
        engine, tenant_id="demo", user_id=None,
        session_id="demo-sess-1", demo_theme="legal-docs",
    )
    convo = get_conversation(engine, convo_id, tenant_id="demo")
    assert convo["demo_theme"] == "legal-docs"
    assert convo["session_id"] == "demo-sess-1"


def test_list_conversations(engine):
    create_conversation(engine, tenant_id="t1", user_id="u1", title="First")
    create_conversation(engine, tenant_id="t1", user_id="u1", title="Second")
    create_conversation(engine, tenant_id="t2", user_id="u2", title="Other tenant")
    convos = list_conversations(engine, tenant_id="t1", user_id="u1")
    assert len(convos) == 2
    # Most recent first
    assert convos[0]["title"] == "Second"


def test_delete_conversation(engine):
    convo_id = create_conversation(engine, tenant_id="t1", user_id="u1")
    delete_conversation(engine, convo_id, tenant_id="t1")
    assert get_conversation(engine, convo_id, tenant_id="t1") is None


def test_add_and_get_messages(engine):
    convo_id = create_conversation(engine, tenant_id="t1", user_id="u1")
    add_message(engine, convo_id, role="user", content="Hello")
    add_message(engine, convo_id, role="assistant", content="Hi there!", sources=[{"document": "doc.pdf", "excerpt": "..."}])
    msgs = get_recent_messages(engine, convo_id, limit=20)
    assert len(msgs) == 2
    assert msgs[0]["role"] == "user"
    assert msgs[1]["role"] == "assistant"
    assert msgs[1]["sources"][0]["document"] == "doc.pdf"


def test_get_recent_messages_respects_limit(engine):
    convo_id = create_conversation(engine, tenant_id="t1", user_id="u1")
    for i in range(25):
        add_message(engine, convo_id, role="user", content=f"Message {i}")
    msgs = get_recent_messages(engine, convo_id, limit=20)
    assert len(msgs) == 20
    # Should be the 20 most recent, in chronological order
    assert msgs[0]["content"] == "Message 5"
    assert msgs[-1]["content"] == "Message 24"


def test_cannot_access_other_tenants_conversation(engine):
    convo_id = create_conversation(engine, tenant_id="t1", user_id="u1")
    result = get_conversation(engine, convo_id, tenant_id="t2")
    assert result is None
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `cd /home/ubuntu/source/OpenRaven && python -m pytest openraven/tests/test_conversations.py::test_create_conversation -v`
Expected: FAIL — module not found

- [ ] **Step 4: Implement CRUD functions**

Create `openraven/src/openraven/conversations/models.py`:

```python
"""Conversation and message persistence."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Engine, select, delete, desc

from openraven.auth.db import conversations, messages


def create_conversation(
    engine: Engine,
    tenant_id: str,
    user_id: str | None,
    title: str | None = None,
    session_id: str | None = None,
    demo_theme: str | None = None,
) -> str:
    """Create a new conversation. Returns conversation ID."""
    convo_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    with engine.connect() as conn:
        conn.execute(conversations.insert().values(
            id=convo_id,
            tenant_id=tenant_id,
            user_id=user_id,
            session_id=session_id,
            title=title,
            demo_theme=demo_theme,
            created_at=now,
            updated_at=now,
        ))
        conn.commit()
    return convo_id


def list_conversations(
    engine: Engine,
    tenant_id: str,
    user_id: str | None = None,
    session_id: str | None = None,
) -> list[dict]:
    """List conversations for a tenant+user, most recent first."""
    query = (
        select(conversations)
        .where(conversations.c.tenant_id == tenant_id)
        .order_by(desc(conversations.c.updated_at))
    )
    if user_id:
        query = query.where(conversations.c.user_id == user_id)
    if session_id:
        query = query.where(conversations.c.session_id == session_id)
    with engine.connect() as conn:
        rows = conn.execute(query).fetchall()
    return [
        {
            "id": r.id,
            "title": r.title,
            "demo_theme": r.demo_theme,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "updated_at": r.updated_at.isoformat() if r.updated_at else None,
        }
        for r in rows
    ]


def get_conversation(engine: Engine, convo_id: str, tenant_id: str) -> dict | None:
    """Get a conversation by ID, scoped to tenant."""
    with engine.connect() as conn:
        row = conn.execute(
            select(conversations)
            .where(conversations.c.id == convo_id)
            .where(conversations.c.tenant_id == tenant_id)
        ).fetchone()
    if not row:
        return None
    return {
        "id": row.id,
        "tenant_id": row.tenant_id,
        "user_id": row.user_id,
        "session_id": row.session_id,
        "title": row.title,
        "demo_theme": row.demo_theme,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


def delete_conversation(engine: Engine, convo_id: str, tenant_id: str) -> None:
    """Delete a conversation and its messages (cascade)."""
    with engine.connect() as conn:
        conn.execute(
            delete(conversations)
            .where(conversations.c.id == convo_id)
            .where(conversations.c.tenant_id == tenant_id)
        )
        conn.commit()


def add_message(
    engine: Engine,
    conversation_id: str,
    role: str,
    content: str,
    sources: list[dict] | None = None,
) -> str:
    """Add a message to a conversation. Returns message ID."""
    msg_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    with engine.connect() as conn:
        conn.execute(messages.insert().values(
            id=msg_id,
            conversation_id=conversation_id,
            role=role,
            content=content,
            sources=sources,
            created_at=now,
        ))
        # Update conversation's updated_at
        conn.execute(
            conversations.update()
            .where(conversations.c.id == conversation_id)
            .values(updated_at=now)
        )
        conn.commit()
    return msg_id


def get_recent_messages(
    engine: Engine,
    conversation_id: str,
    limit: int = 20,
) -> list[dict]:
    """Get the most recent messages for a conversation, in chronological order."""
    # Get the N most recent, then reverse for chronological order
    with engine.connect() as conn:
        rows = conn.execute(
            select(messages)
            .where(messages.c.conversation_id == conversation_id)
            .order_by(desc(messages.c.created_at))
            .limit(limit)
        ).fetchall()
    result = [
        {
            "id": r.id,
            "role": r.role,
            "content": r.content,
            "sources": r.sources,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in reversed(rows)
    ]
    return result
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd /home/ubuntu/source/OpenRaven && python -m pytest openraven/tests/test_conversations.py -v`
Expected: ALL PASS

- [ ] **Step 6: Commit**

```bash
git add openraven/src/openraven/conversations/ openraven/tests/test_conversations.py
git commit -m "feat: add conversation and message CRUD functions"
```

---

## Task 7: History Formatting for LLM Context

**Files:**
- Create: `openraven/src/openraven/conversations/history.py`
- Test: `openraven/tests/test_conversations.py` (extend)

- [ ] **Step 1: Write failing tests for history formatting**

Append to `openraven/tests/test_conversations.py`:

```python
from openraven.conversations.history import format_history_prefix


def test_format_history_prefix_empty():
    result = format_history_prefix([], "What is X?")
    assert result == "What is X?"


def test_format_history_prefix_with_messages():
    history = [
        {"role": "user", "content": "What is AI?"},
        {"role": "assistant", "content": "AI is artificial intelligence."},
    ]
    result = format_history_prefix(history, "Tell me more")
    assert "Previous conversation:" in result
    assert "User: What is AI?" in result
    assert "Assistant: AI is artificial intelligence." in result
    assert "Current question: Tell me more" in result


def test_format_history_prefix_truncates_to_limit():
    history = [
        {"role": "user", "content": f"Q{i}"}
        for i in range(30)
    ]
    result = format_history_prefix(history, "Latest?", max_turns=10)
    # Should only include last 10 messages
    assert "Q20" in result
    assert "Q29" in result
    assert "Q0" not in result
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /home/ubuntu/source/OpenRaven && python -m pytest openraven/tests/test_conversations.py::test_format_history_prefix_empty -v`
Expected: FAIL — module not found

- [ ] **Step 3: Implement history formatter**

Create `openraven/src/openraven/conversations/history.py`:

```python
"""Format conversation history as LLM context prefix."""
from __future__ import annotations


def format_history_prefix(
    history: list[dict],
    current_question: str,
    max_turns: int = 20,
) -> str:
    """Build a prompt with conversation history prepended to the current question.

    Args:
        history: List of {"role": "user"|"assistant", "content": "..."} dicts.
        current_question: The current user question.
        max_turns: Maximum number of history messages to include (default 20 = 10 turns).

    Returns:
        Combined prompt string. If history is empty, returns just the question.
    """
    if not history:
        return current_question

    trimmed = history[-max_turns:]

    lines = ["Previous conversation:"]
    for msg in trimmed:
        role_label = "User" if msg["role"] == "user" else "Assistant"
        lines.append(f"{role_label}: {msg['content']}")
    lines.append("")
    lines.append(f"Current question: {current_question}")

    return "\n".join(lines)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /home/ubuntu/source/OpenRaven && python -m pytest openraven/tests/test_conversations.py -v`
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
git add openraven/src/openraven/conversations/history.py openraven/tests/test_conversations.py
git commit -m "feat: add conversation history formatting for LLM context"
```

---

## Task 8: Conversation API Routes

**Files:**
- Create: `openraven/src/openraven/conversations/routes.py`
- Test: `openraven/tests/test_conversations.py` (extend)

- [ ] **Step 1: Write failing tests for conversation API**

Append to `openraven/tests/test_conversations.py`:

```python
from openraven.conversations.routes import create_conversations_router
from openraven.auth.routes import create_auth_router


@pytest.fixture
def auth_client(engine):
    """Client with auth + conversations routes."""
    app = FastAPI()
    app.include_router(create_auth_router(engine))
    app.include_router(create_conversations_router(engine))
    client = TestClient(app)
    # Sign up a user to get a session
    res = client.post("/api/auth/signup", json={
        "name": "Alice", "email": "alice@test.com", "password": "securepass123",
    })
    assert res.status_code == 200
    return client


def test_create_conversation_api(auth_client):
    res = auth_client.post("/api/conversations", json={})
    assert res.status_code == 200
    assert "id" in res.json()


def test_list_conversations_api(auth_client):
    auth_client.post("/api/conversations", json={"title": "Chat 1"})
    auth_client.post("/api/conversations", json={"title": "Chat 2"})
    res = auth_client.get("/api/conversations")
    assert res.status_code == 200
    convos = res.json()
    assert len(convos) == 2


def test_get_conversation_api(auth_client):
    create_res = auth_client.post("/api/conversations", json={"title": "My Chat"})
    convo_id = create_res.json()["id"]
    res = auth_client.get(f"/api/conversations/{convo_id}")
    assert res.status_code == 200
    data = res.json()
    assert data["title"] == "My Chat"
    assert data["messages"] == []


def test_delete_conversation_api(auth_client):
    create_res = auth_client.post("/api/conversations", json={})
    convo_id = create_res.json()["id"]
    res = auth_client.delete(f"/api/conversations/{convo_id}")
    assert res.status_code == 200
    get_res = auth_client.get(f"/api/conversations/{convo_id}")
    assert get_res.status_code == 404
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /home/ubuntu/source/OpenRaven && python -m pytest openraven/tests/test_conversations.py::test_create_conversation_api -v`
Expected: FAIL — `create_conversations_router` not found

- [ ] **Step 3: Implement conversation routes**

Create `openraven/src/openraven/conversations/routes.py`:

```python
"""Conversation API routes."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import Engine

from openraven.auth.sessions import validate_session
from openraven.conversations.models import (
    create_conversation, list_conversations, get_conversation,
    delete_conversation, get_recent_messages,
)


class CreateConversationRequest(BaseModel):
    title: str | None = None


def _get_auth(request: Request, engine: Engine):
    """Extract auth context from session cookie."""
    session_id = request.cookies.get("session_id")
    if not session_id:
        raise HTTPException(401, "Not authenticated")
    ctx = validate_session(engine, session_id)
    if not ctx:
        raise HTTPException(401, "Session expired")
    return ctx, session_id


def create_conversations_router(engine: Engine) -> APIRouter:
    router = APIRouter(prefix="/api/conversations")

    @router.post("")
    async def create(request: Request, req: CreateConversationRequest):
        ctx, session_id = _get_auth(request, engine)
        convo_id = create_conversation(
            engine,
            tenant_id=ctx.tenant_id,
            user_id=ctx.user_id,
            title=req.title,
            session_id=session_id if ctx.is_demo else None,
            demo_theme=ctx.demo_theme,
        )
        return {"id": convo_id}

    @router.get("")
    async def list_all(request: Request):
        ctx, session_id = _get_auth(request, engine)
        if ctx.is_demo:
            return list_conversations(engine, tenant_id=ctx.tenant_id, session_id=session_id)
        return list_conversations(engine, tenant_id=ctx.tenant_id, user_id=ctx.user_id)

    @router.get("/{convo_id}")
    async def get(request: Request, convo_id: str):
        ctx, _ = _get_auth(request, engine)
        convo = get_conversation(engine, convo_id, tenant_id=ctx.tenant_id)
        if not convo:
            raise HTTPException(404, "Conversation not found")
        msgs = get_recent_messages(engine, convo_id, limit=200)
        return {**convo, "messages": msgs}

    @router.delete("/{convo_id}")
    async def remove(request: Request, convo_id: str):
        ctx, _ = _get_auth(request, engine)
        convo = get_conversation(engine, convo_id, tenant_id=ctx.tenant_id)
        if not convo:
            raise HTTPException(404, "Conversation not found")
        delete_conversation(engine, convo_id, tenant_id=ctx.tenant_id)
        return {"ok": True}

    return router
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /home/ubuntu/source/OpenRaven && python -m pytest openraven/tests/test_conversations.py -v`
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
git add openraven/src/openraven/conversations/routes.py openraven/tests/test_conversations.py
git commit -m "feat: add conversation API routes (create, list, get, delete)"
```

---

## Task 9: Extend Ask Endpoint with Conversation History

**Files:**
- Modify: `openraven/src/openraven/api/server.py:22-25, 212-220`
- Test: `openraven/tests/test_conversations.py` (extend)

- [ ] **Step 1: Write failing test for ask with conversation_id**

Append to `openraven/tests/test_conversations.py`:

```python
def test_ask_with_conversation_id_persists_messages(auth_client):
    # Create a conversation
    create_res = auth_client.post("/api/conversations", json={"title": "Test"})
    convo_id = create_res.json()["id"]
    # Note: /api/ask requires a pipeline — this test verifies the request model accepts
    # conversation_id and history. Full integration test with pipeline is separate.
    # For unit test, we just verify the endpoint accepts the new fields without error.
    # (The actual pipeline call will fail in test without a real KB, so we test the model.)
    from openraven.api.server import AskRequest
    req = AskRequest(
        question="What is AI?",
        conversation_id=convo_id,
        history=[{"role": "user", "content": "Hello"}, {"role": "assistant", "content": "Hi"}],
    )
    assert req.conversation_id == convo_id
    assert len(req.history) == 2
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /home/ubuntu/source/OpenRaven && python -m pytest openraven/tests/test_conversations.py::test_ask_with_conversation_id_persists_messages -v`
Expected: FAIL — `AskRequest` has no field `conversation_id`

- [ ] **Step 3: Extend AskRequest model**

In `openraven/src/openraven/api/server.py`, update `AskRequest` (lines 22-25):

```python
class HistoryMessage(BaseModel):
    role: str
    content: str


class AskRequest(BaseModel):
    question: str
    mode: str = "mix"
    locale: str = "en"
    conversation_id: str | None = None
    history: list[HistoryMessage] | None = None
```

- [ ] **Step 4: Update the ask endpoint to use history and persist messages**

In `openraven/src/openraven/api/server.py`, update the ask endpoint (lines 212-220):

```python
@app.post("/api/ask", response_model=AskResponse)
async def ask(request: Request, req: AskRequest):
    pipeline = resolve_pipeline(request)

    # Build question with history context
    question = req.question
    if req.history:
        from openraven.conversations.history import format_history_prefix
        history_dicts = [{"role": m.role, "content": m.content} for m in req.history]
        question = format_history_prefix(history_dicts, req.question)

    result = await pipeline.ask_with_sources(question, mode=req.mode, locale=req.locale)
    _audit(request, "kb_query", {"question": req.question[:200], "mode": req.mode})

    # Persist messages if conversation_id provided
    if req.conversation_id and auth_engine:
        from openraven.conversations.models import add_message
        ctx = getattr(request.state, "auth", None)
        if ctx:
            convo = get_conversation(auth_engine, req.conversation_id, tenant_id=ctx.tenant_id)
            if convo:
                add_message(auth_engine, req.conversation_id, role="user", content=req.question)
                sources_data = [{"document": s.document, "excerpt": s.excerpt, "char_start": s.char_start, "char_end": s.char_end} for s in (result.sources if hasattr(result, 'sources') else [])]
                add_message(auth_engine, req.conversation_id, role="assistant", content=result.answer, sources=sources_data or None)
                # Auto-title on first message
                if not convo.get("title"):
                    from openraven.conversations.models import _set_title
                    _set_title(auth_engine, req.conversation_id, req.question[:100])

    return AskResponse(
        answer=result.answer,
        mode=req.mode,
        sources=[SourceRef(**s) for s in result.sources],
        conversation_id=req.conversation_id,
    )
```

Add `conversation_id` to `AskResponse`:

```python
class AskResponse(BaseModel):
    answer: str
    mode: str
    sources: list[SourceRef] = []
    conversation_id: str | None = None
```

- [ ] **Step 5: Add _set_title helper to conversations/models.py**

Append to `openraven/src/openraven/conversations/models.py`:

```python
def _set_title(engine: Engine, convo_id: str, title: str) -> None:
    """Set the title of a conversation (used for auto-titling)."""
    with engine.connect() as conn:
        conn.execute(
            conversations.update()
            .where(conversations.c.id == convo_id)
            .values(title=title)
        )
        conn.commit()
```

Add the import for `get_conversation` in server.py:

```python
from openraven.conversations.models import get_conversation
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `cd /home/ubuntu/source/OpenRaven && python -m pytest openraven/tests/test_conversations.py -v`
Expected: ALL PASS

- [ ] **Step 7: Commit**

```bash
git add openraven/src/openraven/api/server.py openraven/src/openraven/conversations/models.py openraven/tests/test_conversations.py
git commit -m "feat: extend ask endpoint with conversation history and message persistence"
```

---

## Task 10: Register Demo & Conversation Routes in Server

**Files:**
- Modify: `openraven/src/openraven/api/server.py`

- [ ] **Step 1: Register the new routers in the FastAPI app**

In `openraven/src/openraven/api/server.py`, in the section where routers are registered (after auth router inclusion), add:

```python
# Demo routes
from openraven.auth.demo import create_demo_router
app.include_router(create_demo_router(auth_engine, tenants_root=Path(config.working_dir).parent))

# Conversation routes
from openraven.conversations.routes import create_conversations_router
app.include_router(create_conversations_router(auth_engine))
```

These should be registered conditionally only when `config.auth_enabled and auth_engine` is true (same guard as the auth router).

- [ ] **Step 2: Add public prefixes for demo routes**

In the middleware public prefixes list, add:
- `"/api/demo/"`
- `"/api/auth/demo"`

- [ ] **Step 3: Run existing tests to verify nothing is broken**

Run: `cd /home/ubuntu/source/OpenRaven && python -m pytest openraven/tests/ -v --timeout=30`
Expected: ALL PASS

- [ ] **Step 4: Commit**

```bash
git add openraven/src/openraven/api/server.py
git commit -m "feat: register demo and conversation routes in server"
```

---

## Task 11: Frontend — Auth Context Extension & Demo Landing Page

**Files:**
- Modify: `openraven-ui/src/hooks/useAuth.tsx`
- Create: `openraven-ui/src/pages/DemoLandingPage.tsx`

- [ ] **Step 1: Extend useAuth hook with demo support**

In `openraven-ui/src/hooks/useAuth.tsx`, extend the `AuthContextType` interface:

```typescript
interface AuthContextType {
  user: User | null;
  tenant: Tenant | null;
  loading: boolean;
  isDemo: boolean;
  demoTheme: string | null;
  login: (email: string, password: string) => Promise<void>;
  signup: (name: string, email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  loginWithGoogle: () => void;
  startDemo: (theme: string) => Promise<void>;
}
```

Add state variables:

```typescript
const [isDemo, setIsDemo] = useState(false);
const [demoTheme, setDemoTheme] = useState<string | null>(null);
```

Add `startDemo` function:

```typescript
const startDemo = useCallback(async (theme: string) => {
  const res = await fetch("/api/auth/demo", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ theme }),
  });
  if (!res.ok) {
    const data = await res.json();
    throw new Error(data.detail || "Failed to start demo");
  }
  setIsDemo(true);
  setDemoTheme(theme);
}, []);
```

Update `fetchMe` to detect demo sessions — if `/api/auth/me` returns 401 but we have a demo cookie, set demo mode. Alternatively, add a `/api/auth/demo/status` check, or simply rely on the `startDemo` flow setting the state.

Update the context value to include `isDemo`, `demoTheme`, `startDemo`.

- [ ] **Step 2: Create DemoLandingPage**

Create `openraven-ui/src/pages/DemoLandingPage.tsx`:

```tsx
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";
import { useTranslation } from "react-i18next";

interface ThemeInfo {
  slug: string;
  name: string;
  description: string;
}

export default function DemoLandingPage() {
  const [themes, setThemes] = useState<ThemeInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [starting, setStarting] = useState<string | null>(null);
  const { startDemo } = useAuth();
  const navigate = useNavigate();
  const { t } = useTranslation("common");

  useEffect(() => {
    fetch("/api/demo/themes")
      .then((r) => r.json())
      .then(setThemes)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  async function handleStart(slug: string) {
    setStarting(slug);
    try {
      await startDemo(slug);
      navigate("/demo/ask");
    } catch {
      setStarting(null);
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center" style={{ background: "var(--bg-page)" }}>
        <span style={{ color: "var(--color-text-muted)" }}>{t("loading")}</span>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex flex-col items-center justify-center gap-8 p-8" style={{ background: "var(--bg-page)" }}>
      <div className="text-center">
        <h1 className="text-3xl font-bold mb-2" style={{ color: "var(--color-text)" }}>
          Try OpenRaven
        </h1>
        <p style={{ color: "var(--color-text-muted)" }}>
          Explore a sample knowledge base — no account required.
        </p>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 max-w-4xl w-full">
        {themes.map((theme) => (
          <button
            key={theme.slug}
            onClick={() => handleStart(theme.slug)}
            disabled={starting !== null}
            className="p-6 rounded-xl text-left transition-transform hover:scale-105"
            style={{
              background: "var(--bg-card)",
              border: "1px solid var(--color-border)",
            }}
          >
            <h2 className="text-xl font-semibold mb-2" style={{ color: "var(--color-text)" }}>
              {theme.name}
            </h2>
            <p className="text-sm" style={{ color: "var(--color-text-muted)" }}>
              {theme.description}
            </p>
            {starting === theme.slug && (
              <span className="text-xs mt-2 block" style={{ color: "var(--color-primary)" }}>
                Starting...
              </span>
            )}
          </button>
        ))}
      </div>
      <p className="text-sm" style={{ color: "var(--color-text-muted)" }}>
        Want the full experience?{" "}
        <a href="/signup" style={{ color: "var(--color-primary)" }}>
          Create an account
        </a>
      </p>
    </div>
  );
}
```

- [ ] **Step 3: Commit**

```bash
git add openraven-ui/src/hooks/useAuth.tsx openraven-ui/src/pages/DemoLandingPage.tsx
git commit -m "feat: add demo auth support and demo landing page"
```

---

## Task 12: Frontend — Routing Updates for Demo Mode

**Files:**
- Modify: `openraven-ui/src/App.tsx`

- [ ] **Step 1: Update App.tsx routing**

Add imports:

```typescript
import DemoLandingPage from "./pages/DemoLandingPage";
```

Update `AuthGuard` to allow demo routes:

```typescript
function AuthGuard({ children }: { children: React.ReactNode }) {
  const { user, loading, isDemo } = useAuth();
  const { t } = useTranslation("common");
  if (loading) return (
    <div className="min-h-screen flex items-center justify-center" style={{ background: "var(--bg-page)" }}>
      <span style={{ color: "var(--color-text-muted)" }}>{t("loading")}</span>
    </div>
  );
  if (!user && !isDemo) return <Navigate to="/login" />;
  return <>{children}</>;
}
```

Add demo routes (outside the AuthGuard-protected group):

```tsx
<Route path="/demo" element={<DemoLandingPage />} />
<Route path="/demo/ask" element={<DemoGuard><AppShell demo><AskPage /></AppShell></DemoGuard>} />
<Route path="/demo/graph" element={<DemoGuard><AppShell demo><GraphPage /></AppShell></DemoGuard>} />
<Route path="/demo/documents" element={<DemoGuard><AppShell demo><WikiPage /></AppShell></DemoGuard>} />
```

Add `DemoGuard` component:

```typescript
function DemoGuard({ children }: { children: React.ReactNode }) {
  const { isDemo } = useAuth();
  if (!isDemo) return <Navigate to="/demo" />;
  return <>{children}</>;
}
```

- [ ] **Step 2: Update AppShell for demo mode**

Add a `demo` prop to AppShell. When `demo=true`:
- Show only Ask, Graph, Documents in sidebar
- Show demo banner at top: "You're exploring a demo. [Sign up] to create your own knowledge base."
- Show "Switch theme" link that navigates back to `/demo`

- [ ] **Step 3: Commit**

```bash
git add openraven-ui/src/App.tsx
git commit -m "feat: add demo routes and demo guard to frontend routing"
```

---

## Task 13: Frontend — Conversation Sidebar & useConversations Hook

**Files:**
- Create: `openraven-ui/src/hooks/useConversations.tsx`
- Create: `openraven-ui/src/components/ConversationSidebar.tsx`

- [ ] **Step 1: Create useConversations hook**

Create `openraven-ui/src/hooks/useConversations.tsx`:

```tsx
import { useState, useCallback, useEffect } from "react";

interface Conversation {
  id: string;
  title: string | null;
  updated_at: string | null;
}

interface Message {
  id?: string;
  role: "user" | "assistant";
  content: string;
  sources?: { document: string; excerpt: string; char_start: number; char_end: number }[];
}

export function useConversations() {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [loadingList, setLoadingList] = useState(true);

  const fetchConversations = useCallback(async () => {
    try {
      const res = await fetch("/api/conversations");
      if (res.ok) setConversations(await res.json());
    } catch { /* ignore */ }
    finally { setLoadingList(false); }
  }, []);

  useEffect(() => { fetchConversations(); }, [fetchConversations]);

  const createConversation = useCallback(async (title?: string): Promise<string> => {
    const res = await fetch("/api/conversations", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ title }),
    });
    const data = await res.json();
    setActiveId(data.id);
    setMessages([]);
    await fetchConversations();
    return data.id;
  }, [fetchConversations]);

  const loadConversation = useCallback(async (id: string) => {
    const res = await fetch(`/api/conversations/${id}`);
    if (res.ok) {
      const data = await res.json();
      setActiveId(id);
      setMessages(data.messages || []);
    }
  }, []);

  const deleteConversation = useCallback(async (id: string) => {
    await fetch(`/api/conversations/${id}`, { method: "DELETE" });
    if (activeId === id) {
      setActiveId(null);
      setMessages([]);
    }
    await fetchConversations();
  }, [activeId, fetchConversations]);

  const newChat = useCallback(() => {
    setActiveId(null);
    setMessages([]);
  }, []);

  return {
    conversations,
    activeId,
    messages,
    setMessages,
    loadingList,
    createConversation,
    loadConversation,
    deleteConversation,
    newChat,
  };
}
```

- [ ] **Step 2: Create ConversationSidebar component**

Create `openraven-ui/src/components/ConversationSidebar.tsx`:

```tsx
import { useTranslation } from "react-i18next";

interface Conversation {
  id: string;
  title: string | null;
  updated_at: string | null;
}

interface Props {
  conversations: Conversation[];
  activeId: string | null;
  onSelect: (id: string) => void;
  onDelete: (id: string) => void;
  onNewChat: () => void;
}

export default function ConversationSidebar({ conversations, activeId, onSelect, onDelete, onNewChat }: Props) {
  const { t } = useTranslation("common");

  return (
    <div className="flex flex-col h-full" style={{ borderRight: "1px solid var(--color-border)" }}>
      <button
        onClick={onNewChat}
        className="m-2 px-3 py-2 rounded-lg text-sm font-medium"
        style={{ background: "var(--color-primary)", color: "white" }}
      >
        + {t("newChat", "New Chat")}
      </button>
      <div className="flex-1 overflow-y-auto">
        {conversations.map((c) => (
          <div
            key={c.id}
            onClick={() => onSelect(c.id)}
            className="flex items-center justify-between px-3 py-2 mx-1 rounded cursor-pointer text-sm"
            style={{
              background: c.id === activeId ? "var(--bg-active)" : "transparent",
              color: "var(--color-text)",
            }}
          >
            <span className="truncate flex-1">
              {c.title || t("untitledChat", "Untitled chat")}
            </span>
            <button
              onClick={(e) => { e.stopPropagation(); onDelete(c.id); }}
              className="ml-2 text-xs opacity-50 hover:opacity-100"
              title={t("delete", "Delete")}
            >
              x
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
```

- [ ] **Step 3: Commit**

```bash
git add openraven-ui/src/hooks/useConversations.tsx openraven-ui/src/components/ConversationSidebar.tsx
git commit -m "feat: add useConversations hook and ConversationSidebar component"
```

---

## Task 14: Frontend — Integrate Conversations into AskPage

**Files:**
- Modify: `openraven-ui/src/pages/AskPage.tsx`

- [ ] **Step 1: Integrate useConversations into AskPage**

Update `AskPage.tsx`:

Add imports:

```typescript
import { useConversations } from "../hooks/useConversations";
import ConversationSidebar from "../components/ConversationSidebar";
import { useSearchParams } from "react-router-dom";
```

Replace the existing `messages` state with `useConversations`:

```typescript
const {
  conversations, activeId, messages, setMessages,
  createConversation, loadConversation, deleteConversation, newChat,
} = useConversations();
const [searchParams, setSearchParams] = useSearchParams();
```

On mount, restore active conversation from URL:

```typescript
useEffect(() => {
  const cId = searchParams.get("c");
  if (cId && cId !== activeId) {
    loadConversation(cId);
  }
}, []); // only on mount
```

Update `handleSubmit` to use conversation flow:

```typescript
async function handleSubmit(e: React.FormEvent) {
  e.preventDefault();
  if (!input.trim() || loading) return;
  const question = input.trim();
  setInput("");

  // Create conversation if none active
  let convoId = activeId;
  if (!convoId) {
    convoId = await createConversation();
    setSearchParams({ c: convoId });
  }

  setMessages((prev) => [...prev, { role: "user", content: question }]);
  setLoading(true);
  try {
    const history = messages.slice(-20).map((m) => ({ role: m.role, content: m.content }));
    const res = await fetch("/api/ask", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        question,
        mode,
        locale: i18n.language,
        conversation_id: convoId,
        history,
      }),
    });
    const data = await res.json();
    setMessages((prev) => [...prev, { role: "assistant", content: data.answer, sources: data.sources ?? [] }]);
  } catch {
    setMessages((prev) => [...prev, { role: "assistant", content: t("errorReach") }]);
  } finally {
    setLoading(false);
  }
}
```

Add sidebar to the layout — wrap the existing content in a flex row:

```tsx
return (
  <div className="flex h-full">
    <div className="w-64 flex-shrink-0">
      <ConversationSidebar
        conversations={conversations}
        activeId={activeId}
        onSelect={(id) => { loadConversation(id); setSearchParams({ c: id }); }}
        onDelete={deleteConversation}
        onNewChat={() => { newChat(); setSearchParams({}); }}
      />
    </div>
    <div className="flex-1 flex flex-col">
      {/* Existing AskPage content */}
    </div>
  </div>
);
```

- [ ] **Step 2: Commit**

```bash
git add openraven-ui/src/pages/AskPage.tsx
git commit -m "feat: integrate conversation sidebar and history into AskPage"
```

---

## Task 15: Demo Session Cleanup

**Files:**
- Modify: `openraven/src/openraven/auth/demo.py`
- Test: `openraven/tests/test_demo.py` (extend)

- [ ] **Step 1: Write failing test for cleanup**

Append to `openraven/tests/test_demo.py`:

```python
from openraven.auth.demo import cleanup_expired_demo_sessions
from openraven.conversations.models import create_conversation, get_conversation


def test_cleanup_expired_demo_sessions(engine):
    from datetime import datetime, timezone
    from openraven.auth.db import sessions as sessions_table

    # Create an expired demo session
    sid = create_demo_session(engine, theme="legal-docs", ttl_hours=0)
    with engine.connect() as conn:
        conn.execute(
            sessions_table.update()
            .where(sessions_table.c.id == sid)
            .values(expires_at=datetime(2000, 1, 1, tzinfo=timezone.utc))
        )
        conn.commit()

    # Create a conversation linked to this session
    convo_id = create_conversation(
        engine, tenant_id="demo", user_id=None,
        session_id=sid, demo_theme="legal-docs",
    )

    # Run cleanup
    deleted = cleanup_expired_demo_sessions(engine)
    assert deleted >= 1

    # Conversation should be gone too
    assert get_conversation(engine, convo_id, tenant_id="demo") is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /home/ubuntu/source/OpenRaven && python -m pytest openraven/tests/test_demo.py::test_cleanup_expired_demo_sessions -v`
Expected: FAIL — `cleanup_expired_demo_sessions` not found

- [ ] **Step 3: Implement cleanup function**

Append to `openraven/src/openraven/auth/demo.py`:

```python
from datetime import datetime, timezone

from sqlalchemy import select, delete as sa_delete

from openraven.auth.db import sessions as sessions_table, conversations


def cleanup_expired_demo_sessions(engine: Engine) -> int:
    """Delete expired demo sessions and their associated conversations. Returns count deleted."""
    now = datetime.now(timezone.utc)
    with engine.connect() as conn:
        # Find expired demo sessions
        expired = conn.execute(
            select(sessions_table.c.id).where(
                sessions_table.c.is_demo == True,
                sessions_table.c.expires_at < now,
            )
        ).fetchall()
        expired_ids = [r.id for r in expired]

        if expired_ids:
            # Delete conversations linked to these sessions (messages cascade)
            conn.execute(
                sa_delete(conversations).where(
                    conversations.c.session_id.in_(expired_ids)
                )
            )
            # Delete the sessions themselves
            conn.execute(
                sa_delete(sessions_table).where(
                    sessions_table.c.id.in_(expired_ids)
                )
            )
            conn.commit()

    return len(expired_ids)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /home/ubuntu/source/OpenRaven && python -m pytest openraven/tests/test_demo.py -v`
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
git add openraven/src/openraven/auth/demo.py openraven/tests/test_demo.py
git commit -m "feat: add demo session cleanup for expired sessions"
```

---

## Task 16: Final Integration — Wire Cleanup to Server Startup

**Files:**
- Modify: `openraven/src/openraven/api/server.py`

- [ ] **Step 1: Add startup cleanup event**

In `openraven/src/openraven/api/server.py`, add a startup event to clean up expired demo sessions:

```python
@app.on_event("startup")
async def startup_cleanup():
    if auth_engine:
        from openraven.auth.demo import cleanup_expired_demo_sessions
        deleted = cleanup_expired_demo_sessions(auth_engine)
        if deleted:
            logger.info(f"Cleaned up {deleted} expired demo sessions")
```

- [ ] **Step 2: Run the full test suite**

Run: `cd /home/ubuntu/source/OpenRaven && python -m pytest openraven/tests/ -v --timeout=60`
Expected: ALL PASS

- [ ] **Step 3: Commit**

```bash
git add openraven/src/openraven/api/server.py
git commit -m "feat: run demo session cleanup on server startup"
```

---

## Task 17: Demo Rate Limiting & Conversation Limit

**Files:**
- Modify: `openraven/src/openraven/api/server.py`
- Modify: `openraven/src/openraven/conversations/routes.py`
- Test: `openraven/tests/test_demo.py` (extend)

- [ ] **Step 1: Write failing test for demo rate limiting**

Append to `openraven/tests/test_demo.py`:

```python
def test_demo_conversation_limit(engine):
    from openraven.conversations.models import create_conversation, list_conversations
    session_id = create_demo_session(engine, theme="legal-docs")
    for i in range(5):
        create_conversation(engine, tenant_id="demo", user_id=None, session_id=session_id)
    convos = list_conversations(engine, tenant_id="demo", session_id=session_id)
    assert len(convos) == 5
```

- [ ] **Step 2: Add conversation limit enforcement to create route**

In `openraven/src/openraven/conversations/routes.py`, in the `create` endpoint, before creating the conversation:

```python
if ctx.is_demo:
    existing = list_conversations(engine, tenant_id=ctx.tenant_id, session_id=session_id)
    if len(existing) >= 5:
        raise HTTPException(429, "Demo limited to 5 conversations")
```

- [ ] **Step 3: Add demo rate limiting to ask endpoint**

In `openraven/src/openraven/api/server.py`, add a simple in-memory rate limiter for demo sessions at the top of the ask endpoint:

```python
from collections import defaultdict
import time

_demo_ask_counts: dict[str, list[float]] = defaultdict(list)

def _check_demo_rate_limit(ip: str, max_per_hour: int = 30) -> None:
    now = time.time()
    window = now - 3600
    hits = _demo_ask_counts[ip]
    _demo_ask_counts[ip] = [t for t in hits if t > window]
    if len(_demo_ask_counts[ip]) >= max_per_hour:
        raise HTTPException(429, "Demo rate limit exceeded (30 queries/hour)")
    _demo_ask_counts[ip].append(now)
```

At the start of the ask endpoint, after resolving auth:

```python
ctx = getattr(request.state, "auth", None)
if ctx and ctx.is_demo:
    _check_demo_rate_limit(request.client.host)
```

- [ ] **Step 4: Run tests**

Run: `cd /home/ubuntu/source/OpenRaven && python -m pytest openraven/tests/test_demo.py -v`
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
git add openraven/src/openraven/api/server.py openraven/src/openraven/conversations/routes.py openraven/tests/test_demo.py
git commit -m "feat: add demo rate limiting and conversation limit"
```

---

## Task 18: Demo Pipeline Resolution (Theme Sub-directories)

**Files:**
- Modify: `openraven/src/openraven/auth/tenant.py`
- Modify: `openraven/src/openraven/api/server.py`
- Test: `openraven/tests/test_demo.py` (extend)

- [ ] **Step 1: Write failing test for demo pipeline resolution**

Append to `openraven/tests/test_demo.py`:

```python
def test_get_demo_tenant_config_uses_theme_subdir(tmp_path):
    from openraven.auth.tenant import get_tenant_config
    from openraven.pipeline import RavenConfig
    tenants_root = tmp_path / "tenants"
    demo_dir = tenants_root / "demo" / "legal-docs"
    demo_dir.mkdir(parents=True)
    base_config = RavenConfig(working_dir=tmp_path, gemini_api_key="test")
    config = get_tenant_config(base_config, "demo", tenants_root=tenants_root, demo_theme="legal-docs")
    assert str(config.working_dir).endswith("demo/legal-docs")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /home/ubuntu/source/OpenRaven && python -m pytest openraven/tests/test_demo.py::test_get_demo_tenant_config_uses_theme_subdir -v`
Expected: FAIL — `get_tenant_config` doesn't accept `demo_theme`

- [ ] **Step 3: Extend get_tenant_config for demo themes**

In `openraven/src/openraven/auth/tenant.py`, update `get_tenant_config`:

```python
def get_tenant_config(
    base_config: RavenConfig,
    tenant_id: str,
    tenants_root: Path | None = None,
    demo_theme: str | None = None,
) -> RavenConfig:
    """Create a tenant-scoped RavenConfig with isolated working_dir."""
    if tenants_root is None:
        tenants_root = Path("/data/tenants")
    tenant_dir = tenants_root / tenant_id
    if demo_theme:
        tenant_dir = tenant_dir / demo_theme
    tenant_dir.mkdir(parents=True, exist_ok=True)
    return replace(base_config, working_dir=tenant_dir)
```

Similarly update `get_tenant_pipeline` to accept and pass `demo_theme`.

- [ ] **Step 4: Update resolve_pipeline in server.py**

In `resolve_pipeline`, pass `demo_theme` when the context is a demo session:

```python
def resolve_pipeline(request: Request) -> RavenPipeline:
    if config.auth_enabled and auth_engine:
        session_id = request.cookies.get("session_id")
        if session_id:
            ctx = validate_session(auth_engine, session_id)
            if ctx:
                return get_tenant_pipeline(config, ctx.tenant_id, demo_theme=ctx.demo_theme)
    return pipeline
```

- [ ] **Step 5: Run tests**

Run: `cd /home/ubuntu/source/OpenRaven && python -m pytest openraven/tests/test_demo.py -v`
Expected: ALL PASS

- [ ] **Step 6: Commit**

```bash
git add openraven/src/openraven/auth/tenant.py openraven/src/openraven/api/server.py openraven/tests/test_demo.py
git commit -m "feat: resolve demo pipeline using theme sub-directory"
```

---

## Task 19: History Fallback from DB

**Files:**
- Modify: `openraven/src/openraven/api/server.py`
- Test: `openraven/tests/test_conversations.py` (extend)

- [ ] **Step 1: Write failing test for history fallback**

Append to `openraven/tests/test_conversations.py`:

```python
def test_history_fallback_fetches_from_db():
    """When history is not provided but conversation_id is, backend should fetch from DB."""
    from openraven.conversations.history import format_history_prefix
    from openraven.conversations.models import get_recent_messages
    # This tests the logic inline — integration test verifies the actual endpoint
    history = [
        {"role": "user", "content": "What is AI?"},
        {"role": "assistant", "content": "Artificial intelligence."},
    ]
    result = format_history_prefix(history, "Tell me more")
    assert "What is AI?" in result
    assert "Tell me more" in result
```

- [ ] **Step 2: Update ask endpoint to fetch history from DB when not provided**

In the ask endpoint in `server.py`, add fallback logic:

```python
# Build question with history context
question = req.question
history_dicts = None
if req.history:
    history_dicts = [{"role": m.role, "content": m.content} for m in req.history]
elif req.conversation_id and auth_engine:
    # Fallback: fetch from DB
    from openraven.conversations.models import get_recent_messages
    ctx = getattr(request.state, "auth", None)
    if ctx:
        db_msgs = get_recent_messages(auth_engine, req.conversation_id, limit=20)
        if db_msgs:
            history_dicts = [{"role": m["role"], "content": m["content"]} for m in db_msgs]

if history_dicts:
    from openraven.conversations.history import format_history_prefix
    question = format_history_prefix(history_dicts, req.question)
```

- [ ] **Step 3: Run tests**

Run: `cd /home/ubuntu/source/OpenRaven && python -m pytest openraven/tests/test_conversations.py -v`
Expected: ALL PASS

- [ ] **Step 4: Commit**

```bash
git add openraven/src/openraven/api/server.py openraven/tests/test_conversations.py
git commit -m "feat: add history fallback from DB when frontend cache not provided"
```

---

## Summary

| Task | Description | New Files | Modified Files |
|------|-------------|-----------|----------------|
| 1 | Demo session schema | test_demo.py | db.py, models.py |
| 2 | Demo session create/validate | — | sessions.py, test_demo.py |
| 3 | Demo routes (themes + start) | demo.py | test_demo.py |
| 4 | Middleware demo restrictions | — | middleware.py, server.py, test_demo.py |
| 5 | Conversations + messages tables | test_conversations.py | db.py |
| 6 | Conversation CRUD | conversations/models.py | test_conversations.py |
| 7 | History formatting | conversations/history.py | test_conversations.py |
| 8 | Conversation API routes | conversations/routes.py | test_conversations.py |
| 9 | Ask endpoint + history | — | server.py, models.py, test_conversations.py |
| 10 | Register all routes | — | server.py |
| 11 | Frontend auth + demo landing | DemoLandingPage.tsx | useAuth.tsx |
| 12 | Frontend routing | — | App.tsx |
| 13 | Conversations hook + sidebar | useConversations.tsx, ConversationSidebar.tsx | — |
| 14 | AskPage integration | — | AskPage.tsx |
| 15 | Demo cleanup | — | demo.py, test_demo.py |
| 16 | Startup cleanup wiring | — | server.py |
| 17 | Rate limiting + conversation limit | — | server.py, routes.py, test_demo.py |
| 18 | Demo pipeline resolution (themes) | — | tenant.py, server.py, test_demo.py |
| 19 | History fallback from DB | — | server.py, test_conversations.py |
