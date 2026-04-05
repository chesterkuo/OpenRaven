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
