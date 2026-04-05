import pytest
import uuid
import os
from datetime import datetime, timezone
from sqlalchemy import insert

from openraven.auth.sessions import create_session, validate_session, delete_session
from openraven.auth.db import get_engine, create_tables, users, tenants, tenant_members


@pytest.fixture
def db_engine():
    engine = get_engine("sqlite:///test_sessions.db")
    create_tables(engine)
    yield engine
    os.remove("test_sessions.db")


@pytest.fixture
def test_user(db_engine):
    user_id = str(uuid.uuid4())
    tenant_id = str(uuid.uuid4())
    with db_engine.connect() as conn:
        conn.execute(insert(users).values(
            id=user_id, email="test@example.com", name="Test User",
            password_hash="$2b$12$fakehashfakehashfakehashfakehashfakehashfakehashfake",
            created_at=datetime.now(timezone.utc), updated_at=datetime.now(timezone.utc),
        ))
        conn.execute(insert(tenants).values(
            id=tenant_id, name="Test Workspace", owner_user_id=user_id,
            created_at=datetime.now(timezone.utc),
        ))
        conn.execute(insert(tenant_members).values(
            tenant_id=tenant_id, user_id=user_id, role="owner",
        ))
        conn.commit()
    return {"user_id": user_id, "tenant_id": tenant_id}


def test_create_session_returns_session_id(db_engine, test_user):
    session_id = create_session(db_engine, test_user["user_id"])
    assert isinstance(session_id, str)
    assert len(session_id) > 20


def test_validate_session_returns_auth_context(db_engine, test_user):
    session_id = create_session(db_engine, test_user["user_id"])
    ctx = validate_session(db_engine, session_id)
    assert ctx is not None
    assert ctx.user_id == test_user["user_id"]
    assert ctx.tenant_id == test_user["tenant_id"]
    assert ctx.email == "test@example.com"


def test_validate_session_expired_returns_none(db_engine, test_user):
    session_id = create_session(db_engine, test_user["user_id"], ttl_hours=-1)
    ctx = validate_session(db_engine, session_id)
    assert ctx is None


def test_delete_session(db_engine, test_user):
    session_id = create_session(db_engine, test_user["user_id"])
    delete_session(db_engine, session_id)
    ctx = validate_session(db_engine, session_id)
    assert ctx is None
