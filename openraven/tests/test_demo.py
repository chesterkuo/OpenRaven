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
