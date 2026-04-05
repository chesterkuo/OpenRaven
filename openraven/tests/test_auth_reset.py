import pytest
import os
import uuid
from datetime import datetime, timezone
from sqlalchemy import insert

from openraven.auth.db import get_engine, create_tables, users
from openraven.auth.passwords import hash_password, verify_password
from openraven.auth.reset import create_reset_token, verify_reset_token, consume_reset_token


@pytest.fixture
def db_engine():
    db_path = f"test_reset_{uuid.uuid4().hex[:8]}.db"
    engine = get_engine(f"sqlite:///{db_path}")
    create_tables(engine)
    yield engine
    os.remove(db_path)


@pytest.fixture
def test_user(db_engine):
    user_id = str(uuid.uuid4())
    with db_engine.connect() as conn:
        conn.execute(insert(users).values(
            id=user_id, email="alice@example.com", name="Alice",
            password_hash=hash_password("oldpass123"),
            created_at=datetime.now(timezone.utc), updated_at=datetime.now(timezone.utc),
        ))
        conn.commit()
    return user_id


def test_create_reset_token_returns_token(db_engine, test_user):
    token = create_reset_token(db_engine, "alice@example.com")
    assert token is not None
    assert len(token) > 20


def test_create_reset_token_nonexistent_email(db_engine):
    token = create_reset_token(db_engine, "nobody@example.com")
    assert token is None


def test_verify_reset_token_valid(db_engine, test_user):
    token = create_reset_token(db_engine, "alice@example.com")
    user_id = verify_reset_token(db_engine, token)
    assert user_id == test_user


def test_verify_reset_token_invalid(db_engine):
    user_id = verify_reset_token(db_engine, "bogus-token")
    assert user_id is None


def test_consume_reset_token_changes_password(db_engine, test_user):
    token = create_reset_token(db_engine, "alice@example.com")
    success = consume_reset_token(db_engine, token, "newpass456")
    assert success is True

    # Verify new password works
    from sqlalchemy import select
    with db_engine.connect() as conn:
        row = conn.execute(select(users.c.password_hash).where(users.c.id == test_user)).first()
    assert verify_password("newpass456", row.password_hash)
    assert not verify_password("oldpass123", row.password_hash)


def test_consume_reset_token_cannot_reuse(db_engine, test_user):
    token = create_reset_token(db_engine, "alice@example.com")
    consume_reset_token(db_engine, token, "newpass456")
    # Second use should fail
    success = consume_reset_token(db_engine, token, "anotherpass")
    assert success is False
