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


from fastapi import FastAPI
from fastapi.testclient import TestClient
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
