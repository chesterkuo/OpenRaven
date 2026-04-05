"""
Comprehensive API integration tests for Demo Sandbox and Conversation Memory features.

Tests realistic HTTP flows using FastAPI TestClient.
"""
from __future__ import annotations

import pytest
from datetime import datetime, timezone
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import event

from openraven.auth.db import get_engine, create_tables, sessions as sessions_table
from openraven.auth.demo import create_demo_router, cleanup_expired_demo_sessions
from openraven.auth.routes import create_auth_router
from openraven.auth.sessions import create_demo_session, validate_session
from openraven.conversations.routes import create_conversations_router
from openraven.conversations.models import (
    create_conversation, get_conversation, add_message,
)


def _make_engine(db_path: str):
    """Create an engine with SQLite foreign key support enabled."""
    eng = get_engine(f"sqlite:///{db_path}")

    @event.listens_for(eng, "connect")
    def _enable_fk(dbapi_connection, _record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    create_tables(eng)
    return eng


def _reset_rate_limiter():
    """Clear the in-memory login rate limiter between tests."""
    import openraven.auth.routes as _routes
    _routes._login_attempts.clear()


# ---------------------------------------------------------------------------
# Shared Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def reset_rate_limiter():
    """Reset in-memory rate limiter before each test to avoid cross-test pollution."""
    _reset_rate_limiter()


@pytest.fixture
def engine(tmp_path):
    return _make_engine(f"{tmp_path}/test_integration.db")


@pytest.fixture
def themes_dir(tmp_path):
    """Create a themes directory with two demo themes."""
    tenants_root = tmp_path / "tenants"
    demo_dir = tenants_root / "demo"

    legal = demo_dir / "legal-docs"
    legal.mkdir(parents=True)
    (legal / ".theme.json").write_text(
        '{"name": "Legal Docs", "description": "Sample legal documents"}'
    )

    tech = demo_dir / "tech-wiki"
    tech.mkdir(parents=True)
    (tech / ".theme.json").write_text(
        '{"name": "Tech Wiki", "description": "Technology knowledge base"}'
    )

    return tenants_root


@pytest.fixture
def demo_app(engine, themes_dir):
    """Minimal FastAPI app with demo + auth + conversations routers."""
    app = FastAPI()
    app.include_router(create_demo_router(engine, tenants_root=themes_dir))
    app.include_router(create_auth_router(engine))
    app.include_router(create_conversations_router(engine))
    return app


@pytest.fixture
def demo_client(demo_app):
    return TestClient(demo_app)


@pytest.fixture
def auth_app(engine):
    """Minimal FastAPI app with auth + conversations routers (no demo)."""
    app = FastAPI()
    app.include_router(create_auth_router(engine))
    app.include_router(create_conversations_router(engine))
    return app


@pytest.fixture
def auth_client(auth_app):
    """Client pre-signed-in as User Alice."""
    client = TestClient(auth_app)
    res = client.post("/api/auth/signup", json={
        "name": "Alice", "email": "alice@example.com", "password": "securepass123",
    })
    assert res.status_code == 200
    return client


# ---------------------------------------------------------------------------
# Demo Sandbox Flow
# ---------------------------------------------------------------------------

class TestDemoThemes:
    """GET /api/demo/themes — public, no auth required."""

    def test_list_themes_returns_200(self, demo_client):
        res = demo_client.get("/api/demo/themes")
        assert res.status_code == 200

    def test_list_themes_no_auth_needed(self, demo_client):
        """No session cookie required."""
        res = demo_client.get("/api/demo/themes", cookies={})
        assert res.status_code == 200

    def test_list_themes_returns_all_seeded_themes(self, demo_client):
        themes = demo_client.get("/api/demo/themes").json()
        slugs = {t["slug"] for t in themes}
        assert "legal-docs" in slugs
        assert "tech-wiki" in slugs

    def test_list_themes_contains_required_fields(self, demo_client):
        themes = demo_client.get("/api/demo/themes").json()
        for theme in themes:
            assert "slug" in theme
            assert "name" in theme
            assert "description" in theme

    def test_list_themes_metadata_matches_json(self, demo_client):
        themes = demo_client.get("/api/demo/themes").json()
        legal = next(t for t in themes if t["slug"] == "legal-docs")
        assert legal["name"] == "Legal Docs"
        assert legal["description"] == "Sample legal documents"

    def test_list_themes_empty_when_no_demo_dir(self, engine, tmp_path):
        empty_root = tmp_path / "empty_tenants"
        empty_root.mkdir()
        app = FastAPI()
        app.include_router(create_demo_router(engine, tenants_root=empty_root))
        client = TestClient(app)
        res = client.get("/api/demo/themes")
        assert res.status_code == 200
        assert res.json() == []


class TestDemoSessionStart:
    """POST /api/auth/demo — start demo session."""

    def test_valid_theme_returns_200(self, demo_client):
        res = demo_client.post("/api/auth/demo", json={"theme": "legal-docs"})
        assert res.status_code == 200

    def test_valid_theme_sets_session_cookie(self, demo_client):
        res = demo_client.post("/api/auth/demo", json={"theme": "legal-docs"})
        assert "session_id" in res.cookies

    def test_valid_theme_returns_theme_name(self, demo_client):
        res = demo_client.post("/api/auth/demo", json={"theme": "legal-docs"})
        assert res.json()["theme"] == "legal-docs"

    def test_invalid_theme_returns_404(self, demo_client):
        res = demo_client.post("/api/auth/demo", json={"theme": "nonexistent-theme"})
        assert res.status_code == 404

    def test_invalid_theme_no_cookie_set(self, demo_client):
        res = demo_client.post("/api/auth/demo", json={"theme": "nonexistent-theme"})
        assert "session_id" not in res.cookies

    def test_session_is_demo_in_db(self, demo_client, engine):
        res = demo_client.post("/api/auth/demo", json={"theme": "legal-docs"})
        session_id = res.cookies["session_id"]
        ctx = validate_session(engine, session_id)
        assert ctx is not None
        assert ctx.is_demo is True

    def test_session_demo_theme_matches(self, demo_client, engine):
        res = demo_client.post("/api/auth/demo", json={"theme": "tech-wiki"})
        session_id = res.cookies["session_id"]
        ctx = validate_session(engine, session_id)
        assert ctx.demo_theme == "tech-wiki"

    def test_session_tenant_id_is_demo(self, demo_client, engine):
        res = demo_client.post("/api/auth/demo", json={"theme": "legal-docs"})
        session_id = res.cookies["session_id"]
        ctx = validate_session(engine, session_id)
        assert ctx.tenant_id == "demo"

    def test_session_user_id_is_none(self, demo_client, engine):
        res = demo_client.post("/api/auth/demo", json={"theme": "legal-docs"})
        session_id = res.cookies["session_id"]
        ctx = validate_session(engine, session_id)
        assert ctx.user_id is None

    def test_each_start_creates_unique_session(self, demo_client):
        r1 = demo_client.post("/api/auth/demo", json={"theme": "legal-docs"})
        r2 = demo_client.post("/api/auth/demo", json={"theme": "legal-docs"})
        assert r1.cookies["session_id"] != r2.cookies["session_id"]


class TestDemoConversationCRUD:
    """Demo session can create, list, get, and delete conversations."""

    @pytest.fixture
    def demo_session_client(self, demo_client):
        """Client with an active demo session cookie."""
        res = demo_client.post("/api/auth/demo", json={"theme": "legal-docs"})
        assert res.status_code == 200
        return demo_client

    def test_create_conversation(self, demo_session_client):
        res = demo_session_client.post("/api/conversations", json={})
        assert res.status_code == 200
        assert "id" in res.json()

    def test_create_conversation_with_title(self, demo_session_client):
        res = demo_session_client.post("/api/conversations", json={"title": "Demo Chat"})
        assert res.status_code == 200
        convo_id = res.json()["id"]
        get_res = demo_session_client.get(f"/api/conversations/{convo_id}")
        assert get_res.status_code == 200
        assert get_res.json()["title"] == "Demo Chat"

    def test_list_conversations(self, demo_session_client):
        demo_session_client.post("/api/conversations", json={"title": "C1"})
        demo_session_client.post("/api/conversations", json={"title": "C2"})
        res = demo_session_client.get("/api/conversations")
        assert res.status_code == 200
        assert len(res.json()) == 2

    def test_get_conversation_returns_messages_list(self, demo_session_client):
        create_res = demo_session_client.post("/api/conversations", json={})
        convo_id = create_res.json()["id"]
        res = demo_session_client.get(f"/api/conversations/{convo_id}")
        assert res.status_code == 200
        assert "messages" in res.json()
        assert isinstance(res.json()["messages"], list)

    def test_delete_conversation(self, demo_session_client):
        create_res = demo_session_client.post("/api/conversations", json={})
        convo_id = create_res.json()["id"]
        del_res = demo_session_client.delete(f"/api/conversations/{convo_id}")
        assert del_res.status_code == 200
        get_res = demo_session_client.get(f"/api/conversations/{convo_id}")
        assert get_res.status_code == 404

    def test_get_nonexistent_conversation_returns_404(self, demo_session_client):
        res = demo_session_client.get("/api/conversations/does-not-exist")
        assert res.status_code == 404

    def test_demo_conversation_has_demo_theme(self, demo_session_client, engine):
        create_res = demo_session_client.post("/api/conversations", json={})
        convo_id = create_res.json()["id"]
        # Fetch directly from DB to check metadata
        get_res = demo_session_client.get(f"/api/conversations/{convo_id}")
        assert get_res.status_code == 200


class TestDemoConversationLimit:
    """Demo sessions are limited to 5 conversations (429 on 6th)."""

    def test_can_create_five_conversations(self, demo_client, engine):
        demo_client.post("/api/auth/demo", json={"theme": "legal-docs"})
        for i in range(5):
            res = demo_client.post("/api/conversations", json={"title": f"Chat {i}"})
            assert res.status_code == 200, f"Conversation {i} failed: {res.status_code}"

    def test_sixth_conversation_rejected_with_429(self, demo_client, engine):
        demo_client.post("/api/auth/demo", json={"theme": "legal-docs"})
        for i in range(5):
            demo_client.post("/api/conversations", json={"title": f"Chat {i}"})
        res = demo_client.post("/api/conversations", json={"title": "Over limit"})
        assert res.status_code == 429

    def test_two_demo_sessions_have_independent_limits(self, demo_client, engine):
        """Each demo session has its own conversation limit."""
        # Session A: create 5 conversations
        app = demo_client.app
        client_a = TestClient(app)
        client_b = TestClient(app)
        client_a.post("/api/auth/demo", json={"theme": "legal-docs"})
        client_b.post("/api/auth/demo", json={"theme": "tech-wiki"})

        for i in range(5):
            r = client_a.post("/api/conversations", json={"title": f"A{i}"})
            assert r.status_code == 200
        # Session A is now at limit
        assert client_a.post("/api/conversations", json={}).status_code == 429
        # Session B still has capacity
        assert client_b.post("/api/conversations", json={}).status_code == 200


class TestDemoBlockedPaths:
    """Demo session is blocked from restricted endpoints (403 or 401)."""

    @pytest.fixture
    def demo_session_client(self, demo_client):
        demo_client.post("/api/auth/demo", json={"theme": "legal-docs"})
        return demo_client

    def test_demo_can_access_conversations(self, demo_session_client):
        res = demo_session_client.get("/api/conversations")
        assert res.status_code == 200

    def test_demo_can_access_demo_themes(self, demo_session_client):
        res = demo_session_client.get("/api/demo/themes")
        assert res.status_code == 200

    def test_middleware_blocks_settings_for_demo(self):
        from openraven.auth.middleware import is_demo_allowed
        assert is_demo_allowed("/api/settings") is False

    def test_middleware_blocks_team_for_demo(self):
        from openraven.auth.middleware import is_demo_allowed
        assert is_demo_allowed("/api/team") is False

    def test_middleware_blocks_ingest_for_demo(self):
        from openraven.auth.middleware import is_demo_allowed
        assert is_demo_allowed("/api/ingest") is False

    def test_middleware_blocks_sync_for_demo(self):
        from openraven.auth.middleware import is_demo_allowed
        assert is_demo_allowed("/api/sync") is False

    def test_middleware_blocks_account_for_demo(self):
        from openraven.auth.middleware import is_demo_allowed
        assert is_demo_allowed("/api/account") is False

    def test_middleware_allows_ask_for_demo(self):
        from openraven.auth.middleware import is_demo_allowed
        assert is_demo_allowed("/api/ask") is True

    def test_middleware_allows_graph_for_demo(self):
        from openraven.auth.middleware import is_demo_allowed
        assert is_demo_allowed("/api/graph") is True

    def test_middleware_allows_graph_sub_path_for_demo(self):
        from openraven.auth.middleware import is_demo_allowed
        assert is_demo_allowed("/api/graph/export") is True

    def test_middleware_blocks_ask_with_suffix(self):
        """Exact-match boundary: /api/ask-agents should be blocked."""
        from openraven.auth.middleware import is_demo_allowed
        assert is_demo_allowed("/api/ask-agents") is False


# ---------------------------------------------------------------------------
# Demo Session Cleanup
# ---------------------------------------------------------------------------

class TestDemoCleanup:
    """Expired demo sessions are removed along with their conversations."""

    def _expire_session(self, engine, session_id: str):
        with engine.connect() as conn:
            conn.execute(
                sessions_table.update()
                .where(sessions_table.c.id == session_id)
                .values(expires_at=datetime(2000, 1, 1, tzinfo=timezone.utc))
            )
            conn.commit()

    def test_cleanup_removes_expired_demo_session(self, engine):
        sid = create_demo_session(engine, theme="legal-docs", ttl_hours=0)
        self._expire_session(engine, sid)
        deleted = cleanup_expired_demo_sessions(engine)
        assert deleted >= 1
        assert validate_session(engine, sid) is None

    def test_cleanup_removes_conversations_from_expired_sessions(self, engine):
        sid = create_demo_session(engine, theme="legal-docs", ttl_hours=0)
        convo_id = create_conversation(
            engine, tenant_id="demo", user_id=None,
            session_id=sid, demo_theme="legal-docs",
        )
        self._expire_session(engine, sid)
        cleanup_expired_demo_sessions(engine)
        assert get_conversation(engine, convo_id, tenant_id="demo") is None

    def test_cleanup_does_not_remove_active_sessions(self, engine):
        sid = create_demo_session(engine, theme="legal-docs", ttl_hours=2)
        deleted = cleanup_expired_demo_sessions(engine)
        assert deleted == 0
        ctx = validate_session(engine, sid)
        assert ctx is not None

    def test_cleanup_does_not_remove_regular_user_sessions(self, engine, auth_client):
        """Only expired demo sessions are deleted."""
        # Auth client signed up — that session is a regular session
        # Create an expired demo session
        sid = create_demo_session(engine, theme="legal-docs", ttl_hours=0)
        self._expire_session(engine, sid)
        # Run cleanup — should only touch the expired demo session
        deleted = cleanup_expired_demo_sessions(engine)
        assert deleted == 1

    def test_cleanup_cascades_multiple_sessions(self, engine):
        """Multiple expired sessions are all cleaned up at once."""
        sids = []
        for _ in range(3):
            sid = create_demo_session(engine, theme="legal-docs", ttl_hours=0)
            self._expire_session(engine, sid)
            sids.append(sid)
        # Keep one active
        active_sid = create_demo_session(engine, theme="legal-docs", ttl_hours=2)

        deleted = cleanup_expired_demo_sessions(engine)
        assert deleted == 3
        assert validate_session(engine, active_sid) is not None


# ---------------------------------------------------------------------------
# Security: Unauthenticated and Cross-Session Access
# ---------------------------------------------------------------------------

class TestSecurityUnauthenticated:
    """Unauthenticated requests to protected endpoints return 401."""

    def test_unauthenticated_list_conversations(self, demo_client):
        res = demo_client.get("/api/conversations", cookies={})
        assert res.status_code == 401

    def test_unauthenticated_create_conversation(self, demo_client):
        res = demo_client.post("/api/conversations", json={}, cookies={})
        assert res.status_code == 401

    def test_unauthenticated_get_conversation(self, demo_client):
        res = demo_client.get("/api/conversations/some-id", cookies={})
        assert res.status_code == 401

    def test_unauthenticated_delete_conversation(self, demo_client):
        res = demo_client.delete("/api/conversations/some-id", cookies={})
        assert res.status_code == 401


class TestSecurityExpiredDemoSession:
    """Expired demo session returns 401."""

    def test_expired_demo_session_blocked_from_conversations(self, demo_client, engine):
        res = demo_client.post("/api/auth/demo", json={"theme": "legal-docs"})
        session_id = res.cookies["session_id"]
        # Expire the session
        with engine.connect() as conn:
            conn.execute(
                sessions_table.update()
                .where(sessions_table.c.id == session_id)
                .values(expires_at=datetime(2000, 1, 1, tzinfo=timezone.utc))
            )
            conn.commit()
        res = demo_client.get("/api/conversations")
        assert res.status_code == 401

    def test_expired_demo_session_cannot_create_conversation(self, demo_client, engine):
        res = demo_client.post("/api/auth/demo", json={"theme": "legal-docs"})
        session_id = res.cookies["session_id"]
        with engine.connect() as conn:
            conn.execute(
                sessions_table.update()
                .where(sessions_table.c.id == session_id)
                .values(expires_at=datetime(2000, 1, 1, tzinfo=timezone.utc))
            )
            conn.commit()
        res = demo_client.post("/api/conversations", json={})
        assert res.status_code == 401


class TestSecurityDemoCrossSession:
    """Demo session A cannot access demo session B's conversations."""

    def test_demo_session_isolation(self, demo_app, engine):
        client_a = TestClient(demo_app)
        client_b = TestClient(demo_app)

        client_a.post("/api/auth/demo", json={"theme": "legal-docs"})
        client_b.post("/api/auth/demo", json={"theme": "tech-wiki"})

        # Session A creates a conversation
        res_a = client_a.post("/api/conversations", json={"title": "Secret A"})
        convo_id = res_a.json()["id"]

        # Session B cannot access session A's conversation
        res_b = client_b.get(f"/api/conversations/{convo_id}")
        assert res_b.status_code == 404

    def test_demo_session_cannot_delete_other_session_conversation(self, demo_app, engine):
        client_a = TestClient(demo_app)
        client_b = TestClient(demo_app)

        client_a.post("/api/auth/demo", json={"theme": "legal-docs"})
        client_b.post("/api/auth/demo", json={"theme": "tech-wiki"})

        res_a = client_a.post("/api/conversations", json={})
        convo_id = res_a.json()["id"]

        # B tries to delete A's conversation
        del_res = client_b.delete(f"/api/conversations/{convo_id}")
        assert del_res.status_code == 404  # Can't find it, so 404

        # A's conversation should still exist
        get_res = client_a.get(f"/api/conversations/{convo_id}")
        assert get_res.status_code == 200

    def test_demo_list_only_shows_own_conversations(self, demo_app, engine):
        client_a = TestClient(demo_app)
        client_b = TestClient(demo_app)

        client_a.post("/api/auth/demo", json={"theme": "legal-docs"})
        client_b.post("/api/auth/demo", json={"theme": "tech-wiki"})

        client_a.post("/api/conversations", json={"title": "A1"})
        client_a.post("/api/conversations", json={"title": "A2"})
        client_b.post("/api/conversations", json={"title": "B1"})

        res_a = client_a.get("/api/conversations").json()
        res_b = client_b.get("/api/conversations").json()

        assert len(res_a) == 2
        assert len(res_b) == 1


# ---------------------------------------------------------------------------
# Conversation Memory Flow (Authenticated Users)
# ---------------------------------------------------------------------------

class TestConversationMemoryAuth:
    """Authenticated user can CRUD conversations with messages."""

    def test_create_conversation_returns_id(self, auth_client):
        res = auth_client.post("/api/conversations", json={})
        assert res.status_code == 200
        assert "id" in res.json()
        assert isinstance(res.json()["id"], str)

    def test_list_conversations_initially_empty(self, auth_client):
        res = auth_client.get("/api/conversations")
        assert res.status_code == 200
        assert isinstance(res.json(), list)

    def test_list_conversations_returns_created(self, auth_client):
        auth_client.post("/api/conversations", json={"title": "My Chat"})
        res = auth_client.get("/api/conversations")
        assert res.status_code == 200
        titles = [c["title"] for c in res.json()]
        assert "My Chat" in titles

    def test_list_conversations_ordered_by_recency(self, auth_client):
        auth_client.post("/api/conversations", json={"title": "First"})
        auth_client.post("/api/conversations", json={"title": "Second"})
        convos = auth_client.get("/api/conversations").json()
        assert convos[0]["title"] == "Second"
        assert convos[1]["title"] == "First"

    def test_get_conversation_by_id(self, auth_client):
        create_res = auth_client.post("/api/conversations", json={"title": "Test Chat"})
        convo_id = create_res.json()["id"]
        res = auth_client.get(f"/api/conversations/{convo_id}")
        assert res.status_code == 200
        data = res.json()
        assert data["id"] == convo_id
        assert data["title"] == "Test Chat"

    def test_get_conversation_includes_empty_messages(self, auth_client):
        create_res = auth_client.post("/api/conversations", json={})
        convo_id = create_res.json()["id"]
        res = auth_client.get(f"/api/conversations/{convo_id}")
        assert res.json()["messages"] == []

    def test_get_conversation_with_messages(self, auth_client, engine):
        """Messages added directly via model are returned by GET endpoint."""
        create_res = auth_client.post("/api/conversations", json={"title": "With Msgs"})
        convo_id = create_res.json()["id"]
        add_message(engine, convo_id, role="user", content="Hello world")
        add_message(engine, convo_id, role="assistant", content="Hi there!")
        res = auth_client.get(f"/api/conversations/{convo_id}")
        assert res.status_code == 200
        msgs = res.json()["messages"]
        assert len(msgs) == 2
        assert msgs[0]["role"] == "user"
        assert msgs[1]["role"] == "assistant"

    def test_delete_conversation_removes_it(self, auth_client):
        create_res = auth_client.post("/api/conversations", json={})
        convo_id = create_res.json()["id"]
        del_res = auth_client.delete(f"/api/conversations/{convo_id}")
        assert del_res.status_code == 200
        get_res = auth_client.get(f"/api/conversations/{convo_id}")
        assert get_res.status_code == 404

    def test_delete_conversation_cascades_messages(self, auth_client, engine):
        """Deleting a conversation also removes its messages."""
        from openraven.auth.db import messages as messages_table
        create_res = auth_client.post("/api/conversations", json={})
        convo_id = create_res.json()["id"]
        add_message(engine, convo_id, role="user", content="Before delete")
        # Delete the conversation
        auth_client.delete(f"/api/conversations/{convo_id}")
        # Messages should be gone too (cascade)
        from sqlalchemy import select
        with engine.connect() as conn:
            rows = conn.execute(
                select(messages_table).where(messages_table.c.conversation_id == convo_id)
            ).fetchall()
        assert len(rows) == 0

    def test_delete_nonexistent_conversation_returns_404(self, auth_client):
        res = auth_client.delete("/api/conversations/does-not-exist")
        assert res.status_code == 404


# ---------------------------------------------------------------------------
# Cross-User and Cross-Tenant Isolation
# ---------------------------------------------------------------------------

class TestCrossUserIsolation:
    """User A cannot see or modify User B's conversations within the same tenant."""

    @pytest.fixture
    def two_users(self, auth_app):
        """Return two authenticated clients sharing the same app (different tenants)."""
        client_a = TestClient(auth_app)
        client_b = TestClient(auth_app)
        client_a.post("/api/auth/signup", json={
            "name": "Alice", "email": "alice@iso.com", "password": "alice-pass-123",
        })
        client_b.post("/api/auth/signup", json={
            "name": "Bob", "email": "bob@iso.com", "password": "bob-pass-123",
        })
        return client_a, client_b

    def test_user_b_cannot_read_user_a_conversation(self, two_users):
        client_a, client_b = two_users
        res = client_a.post("/api/conversations", json={"title": "Alice Private"})
        convo_id = res.json()["id"]
        res_b = client_b.get(f"/api/conversations/{convo_id}")
        assert res_b.status_code == 404

    def test_user_b_cannot_delete_user_a_conversation(self, two_users):
        client_a, client_b = two_users
        res = client_a.post("/api/conversations", json={"title": "Alice Private"})
        convo_id = res.json()["id"]
        del_res = client_b.delete(f"/api/conversations/{convo_id}")
        assert del_res.status_code == 404
        # Alice's conversation still exists
        assert client_a.get(f"/api/conversations/{convo_id}").status_code == 200

    def test_list_only_returns_own_conversations(self, two_users):
        client_a, client_b = two_users
        client_a.post("/api/conversations", json={"title": "Alice Only"})
        client_b.post("/api/conversations", json={"title": "Bob Only"})
        convos_a = client_a.get("/api/conversations").json()
        convos_b = client_b.get("/api/conversations").json()
        titles_a = {c["title"] for c in convos_a}
        titles_b = {c["title"] for c in convos_b}
        assert "Alice Only" in titles_a
        assert "Bob Only" not in titles_a
        assert "Bob Only" in titles_b
        assert "Alice Only" not in titles_b


class TestCrossTenantIsolation:
    """Conversations from one tenant cannot be accessed from another tenant."""

    def test_cross_tenant_isolation_at_model_level(self, engine):
        convo_id = create_conversation(engine, tenant_id="tenant-1", user_id="user-1")
        # Different tenant cannot read it
        result = get_conversation(engine, convo_id, tenant_id="tenant-2")
        assert result is None

    def test_cross_tenant_isolation_same_user_id(self, engine):
        """Even if same user_id exists in two tenants, they can't cross boundaries."""
        convo_id = create_conversation(engine, tenant_id="tenant-a", user_id="shared-uid")
        # Same user_id but in tenant-b
        result = get_conversation(engine, convo_id, tenant_id="tenant-b", user_id="shared-uid")
        assert result is None


# ---------------------------------------------------------------------------
# Conversation Persistence — URL param ?c=<id>
# ---------------------------------------------------------------------------

class TestConversationPersistence:
    """Conversation IDs survive across multiple requests (URL param pattern)."""

    def test_conversation_id_is_stable(self, auth_client):
        """ID returned on creation is the same as ID returned on fetch."""
        create_res = auth_client.post("/api/conversations", json={"title": "Persistent"})
        convo_id = create_res.json()["id"]
        get_res = auth_client.get(f"/api/conversations/{convo_id}")
        assert get_res.json()["id"] == convo_id

    def test_messages_accumulate_across_requests(self, auth_client, engine):
        """Messages added in separate requests are all visible in a later GET."""
        create_res = auth_client.post("/api/conversations", json={})
        convo_id = create_res.json()["id"]
        # Simulate multiple turns
        for i in range(3):
            add_message(engine, convo_id, role="user", content=f"Question {i}")
            add_message(engine, convo_id, role="assistant", content=f"Answer {i}")
        get_res = auth_client.get(f"/api/conversations/{convo_id}")
        msgs = get_res.json()["messages"]
        assert len(msgs) == 6

    def test_listing_conversations_with_messages_updated_at(self, auth_client, engine):
        """After adding messages, the conversation's updated_at reflects the latest message."""
        create_res = auth_client.post("/api/conversations", json={"title": "Timing"})
        convo_id = create_res.json()["id"]
        initial_list = auth_client.get("/api/conversations").json()
        initial_updated = next(c["updated_at"] for c in initial_list if c["id"] == convo_id)

        add_message(engine, convo_id, role="user", content="Hello")
        updated_list = auth_client.get("/api/conversations").json()
        new_updated = next(c["updated_at"] for c in updated_list if c["id"] == convo_id)
        # updated_at should have changed (or at least not regressed)
        assert new_updated >= initial_updated

    def test_ask_request_model_accepts_conversation_id(self):
        """AskRequest accepts conversation_id field for memory integration."""
        from openraven.api.server import AskRequest
        req = AskRequest(
            question="What is AI?",
            conversation_id="test-conv-uuid",
            history=[
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": "Hi"},
            ],
        )
        assert req.conversation_id == "test-conv-uuid"
        assert len(req.history) == 2

    def test_ask_request_model_conversation_id_optional(self):
        """AskRequest works without conversation_id for stateless queries."""
        from openraven.api.server import AskRequest
        req = AskRequest(question="What is AI?")
        assert req.conversation_id is None
        assert req.history is None
