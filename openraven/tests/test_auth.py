import pytest
from openraven.auth.db import create_tables, get_engine
from openraven.auth.models import UserCreate
from openraven.auth.passwords import hash_password, verify_password


def test_create_tables_creates_users_table(tmp_path):
    """Tables should be created without error on a fresh SQLite DB."""
    engine = get_engine(f"sqlite:///{tmp_path}/test_auth.db")
    create_tables(engine)
    from sqlalchemy import inspect
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    assert "users" in tables
    assert "sessions" in tables
    assert "tenants" in tables
    assert "tenant_members" in tables
    assert "password_reset_tokens" in tables


def test_user_create_model_validates_email():
    user = UserCreate(name="Test", email="test@example.com", password="securepass123")
    assert user.email == "test@example.com"
    assert user.name == "Test"


def test_hash_password_returns_bcrypt_hash():
    hashed = hash_password("mysecret123")
    assert hashed.startswith("$2b$")
    assert len(hashed) == 60


def test_verify_password_correct():
    hashed = hash_password("mysecret123")
    assert verify_password("mysecret123", hashed) is True


def test_verify_password_incorrect():
    hashed = hash_password("mysecret123")
    assert verify_password("wrongpassword", hashed) is False
