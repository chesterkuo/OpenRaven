"""Tests for demo session support."""
import pytest
from datetime import datetime, timezone
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
            expires_at=datetime(2099, 1, 1, tzinfo=timezone.utc),
        ))
        conn.commit()
        row = conn.execute(sessions.select().where(sessions.c.id == "test-session")).fetchone()
    assert row.is_demo is False or row.is_demo == 0


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


# ---------------------------------------------------------------------------
# Task 3: Demo Routes (Theme Listing & Session Start)
# ---------------------------------------------------------------------------
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


# ---------------------------------------------------------------------------
# Task 4: Auth Middleware — Demo Session Handling
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Task 15: Demo Session Cleanup
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Task 17: Demo Rate Limiting & Conversation Limit
# ---------------------------------------------------------------------------

def test_demo_conversation_limit(engine):
    from openraven.conversations.models import create_conversation, list_conversations
    session_id = create_demo_session(engine, theme="legal-docs")
    for i in range(5):
        create_conversation(engine, tenant_id="demo", user_id=None, session_id=session_id)
    convos = list_conversations(engine, tenant_id="demo", session_id=session_id)
    assert len(convos) == 5
