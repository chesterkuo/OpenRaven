"""End-to-end tests for Demo Sandbox & Conversation Memory.

Starts a real uvicorn server with auth enabled and runs HTTP requests.
Tests the full request lifecycle including middleware, auth, and route handling.
"""
import os
import time
import json
import pytest
import threading
import requests
from pathlib import Path

import uvicorn
from openraven.api.server import create_app
from openraven.config import RavenConfig


@pytest.fixture(scope="module")
def e2e_server(tmp_path_factory):
    """Start a real uvicorn server with auth enabled for E2E testing."""
    tmp = tmp_path_factory.mktemp("e2e")
    db_path = tmp / "e2e.db"

    # working_dir is inside tmp; server sets tenants_root = working_dir.parent (= tmp)
    working_dir = tmp / "kb"
    working_dir.mkdir()

    # create_app passes tenants_root=config.working_dir.parent to create_demo_router.
    # _list_themes scans tenants_root/"demo", so themes go at tmp/"demo"/<slug>/
    demo_dir = tmp / "demo"

    legal = demo_dir / "legal-docs"
    legal.mkdir(parents=True)
    (legal / ".theme.json").write_text(json.dumps({
        "name": "Legal Documents",
        "description": "Sample legal documents for demo",
    }))

    tech = demo_dir / "tech-wiki"
    tech.mkdir(parents=True)
    (tech / ".theme.json").write_text(json.dumps({
        "name": "Tech Wiki",
        "description": "Technical documentation",
    }))

    os.environ["DATABASE_URL"] = f"sqlite:///{db_path}"

    config = RavenConfig(
        working_dir=working_dir,
        database_url=f"sqlite:///{db_path}",
        api_port=18741,
    )

    app = create_app(config)

    server_config = uvicorn.Config(app, host="127.0.0.1", port=18741, log_level="warning")
    server = uvicorn.Server(server_config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()

    # Wait for server to become healthy
    base = "http://127.0.0.1:18741"
    for _ in range(30):
        try:
            r = requests.get(f"{base}/health", timeout=1)
            if r.ok:
                break
        except Exception:
            pass
        time.sleep(0.5)
    else:
        pytest.fail("E2E server did not start within 15 seconds")

    yield base

    server.should_exit = True
    thread.join(timeout=5)

    os.environ.pop("DATABASE_URL", None)


class TestE2EDemoSandbox:
    """Full lifecycle tests for demo sandbox."""

    def test_demo_themes_accessible_without_auth(self, e2e_server):
        """Demo themes endpoint is public — no session needed."""
        res = requests.get(f"{e2e_server}/api/demo/themes")
        assert res.status_code == 200
        themes = res.json()
        assert len(themes) == 2
        slugs = {t["slug"] for t in themes}
        assert slugs == {"legal-docs", "tech-wiki"}

    def test_full_demo_flow(self, e2e_server):
        """Complete demo flow: pick theme → get session → create conversation → ask."""
        session = requests.Session()

        # 1. List themes
        res = session.get(f"{e2e_server}/api/demo/themes")
        assert res.status_code == 200
        themes = res.json()
        assert len(themes) >= 1

        # 2. Start demo with first theme
        res = session.post(f"{e2e_server}/api/auth/demo", json={"theme": "legal-docs"})
        assert res.status_code == 200
        assert "session_id" in session.cookies
        data = res.json()
        assert data["theme"] == "legal-docs"

        # 3. Create a conversation
        res = session.post(f"{e2e_server}/api/conversations", json={"title": "My Demo Chat"})
        assert res.status_code == 200
        convo_id = res.json()["id"]
        assert len(convo_id) == 36  # UUID format

        # 4. List conversations
        res = session.get(f"{e2e_server}/api/conversations")
        assert res.status_code == 200
        convos = res.json()
        assert len(convos) == 1
        assert convos[0]["title"] == "My Demo Chat"

        # 5. Get conversation detail
        res = session.get(f"{e2e_server}/api/conversations/{convo_id}")
        assert res.status_code == 200
        detail = res.json()
        assert detail["title"] == "My Demo Chat"
        assert detail["messages"] == []

        # 6. Delete conversation
        res = session.delete(f"{e2e_server}/api/conversations/{convo_id}")
        assert res.status_code == 200

        # 7. Confirm deleted
        res = session.get(f"{e2e_server}/api/conversations/{convo_id}")
        assert res.status_code == 404

    def test_demo_blocked_from_protected_routes(self, e2e_server):
        """Demo session cannot access protected routes."""
        session = requests.Session()
        session.post(f"{e2e_server}/api/auth/demo", json={"theme": "legal-docs"})

        # These should all be blocked with 403
        for path in ["/api/team", "/api/account", "/api/settings", "/api/sync"]:
            res = session.get(f"{e2e_server}{path}")
            assert res.status_code == 403, (
                f"Expected 403 for {path}, got {res.status_code}"
            )

    def test_demo_conversation_limit(self, e2e_server):
        """Demo sessions are limited to 5 conversations."""
        session = requests.Session()
        session.post(f"{e2e_server}/api/auth/demo", json={"theme": "tech-wiki"})

        for i in range(5):
            res = session.post(
                f"{e2e_server}/api/conversations", json={"title": f"Chat {i}"}
            )
            assert res.status_code == 200, f"Conversation {i} failed: {res.status_code}"

        # 6th should be rejected
        res = session.post(
            f"{e2e_server}/api/conversations", json={"title": "Chat 5"}
        )
        assert res.status_code == 429

    def test_demo_sessions_isolated(self, e2e_server):
        """Two demo sessions cannot see each other's conversations."""
        session_a = requests.Session()
        session_b = requests.Session()

        session_a.post(f"{e2e_server}/api/auth/demo", json={"theme": "legal-docs"})
        session_b.post(f"{e2e_server}/api/auth/demo", json={"theme": "legal-docs"})

        # A creates a conversation
        res = session_a.post(
            f"{e2e_server}/api/conversations", json={"title": "A's chat"}
        )
        convo_id = res.json()["id"]

        # B cannot see it in list
        res = session_b.get(f"{e2e_server}/api/conversations")
        assert len(res.json()) == 0

        # B cannot access it directly
        res = session_b.get(f"{e2e_server}/api/conversations/{convo_id}")
        assert res.status_code == 404


class TestE2EConversationMemory:
    """Full lifecycle tests for authenticated conversation memory."""

    def test_full_auth_conversation_flow(self, e2e_server):
        """Signup → create conversation → list → get → delete."""
        session = requests.Session()

        # 1. Sign up
        res = session.post(f"{e2e_server}/api/auth/signup", json={
            "name": "E2E User",
            "email": "e2e@test.com",
            "password": "securepass123",
        })
        assert res.status_code == 200

        # 2. Create conversation
        res = session.post(
            f"{e2e_server}/api/conversations", json={"title": "E2E Chat"}
        )
        assert res.status_code == 200
        convo_id = res.json()["id"]

        # 3. List conversations
        res = session.get(f"{e2e_server}/api/conversations")
        assert res.status_code == 200
        convos = res.json()
        assert len(convos) == 1
        assert convos[0]["title"] == "E2E Chat"

        # 4. Get conversation with messages
        res = session.get(f"{e2e_server}/api/conversations/{convo_id}")
        assert res.status_code == 200
        assert res.json()["messages"] == []

        # 5. Create multiple conversations
        for i in range(3):
            session.post(
                f"{e2e_server}/api/conversations", json={"title": f"Chat {i}"}
            )

        res = session.get(f"{e2e_server}/api/conversations")
        assert len(res.json()) == 4

        # 6. Delete one
        session.delete(f"{e2e_server}/api/conversations/{convo_id}")
        res = session.get(f"{e2e_server}/api/conversations")
        assert len(res.json()) == 3

    def test_cross_user_isolation(self, e2e_server):
        """User B cannot access User A's conversations."""
        user_a = requests.Session()
        user_b = requests.Session()

        user_a.post(f"{e2e_server}/api/auth/signup", json={
            "name": "User A", "email": "a-e2e@test.com", "password": "securepass123",
        })
        user_b.post(f"{e2e_server}/api/auth/signup", json={
            "name": "User B", "email": "b-e2e@test.com", "password": "securepass123",
        })

        # A creates conversation
        res = user_a.post(
            f"{e2e_server}/api/conversations", json={"title": "A's secret"}
        )
        convo_id = res.json()["id"]

        # B cannot list it
        res = user_b.get(f"{e2e_server}/api/conversations")
        assert all(c["id"] != convo_id for c in res.json())

        # B cannot access it directly
        res = user_b.get(f"{e2e_server}/api/conversations/{convo_id}")
        assert res.status_code == 404

    def test_unauthenticated_access_blocked(self, e2e_server):
        """Unauthenticated requests to conversation endpoints are blocked."""
        res = requests.get(f"{e2e_server}/api/conversations")
        assert res.status_code == 401

        res = requests.post(f"{e2e_server}/api/conversations", json={})
        assert res.status_code == 401
