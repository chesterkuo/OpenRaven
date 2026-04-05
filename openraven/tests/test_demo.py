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
