import pytest
import os
from fastapi.testclient import TestClient
from fastapi import FastAPI
from openraven.auth.db import get_engine, create_tables
from openraven.auth.routes import create_auth_router


@pytest.fixture
def client():
    engine = get_engine("sqlite:///test_auth_api.db")
    create_tables(engine)
    app = FastAPI()
    app.include_router(create_auth_router(engine))
    yield TestClient(app)
    os.remove("test_auth_api.db")


def test_signup_creates_user(client):
    res = client.post("/api/auth/signup", json={
        "name": "Alice", "email": "alice@example.com", "password": "securepass123"
    })
    assert res.status_code == 200
    data = res.json()
    assert data["user"]["email"] == "alice@example.com"
    assert data["user"]["name"] == "Alice"


def test_signup_sets_session_cookie(client):
    res = client.post("/api/auth/signup", json={
        "name": "Bob", "email": "bob@example.com", "password": "securepass123"
    })
    assert "session_id" in res.cookies


def test_signup_duplicate_email_fails(client):
    client.post("/api/auth/signup", json={
        "name": "Alice", "email": "alice@example.com", "password": "securepass123"
    })
    res = client.post("/api/auth/signup", json={
        "name": "Alice2", "email": "alice@example.com", "password": "otherpass123"
    })
    assert res.status_code == 409


def test_login_valid_credentials(client):
    client.post("/api/auth/signup", json={
        "name": "Alice", "email": "alice@example.com", "password": "securepass123"
    })
    res = client.post("/api/auth/login", json={
        "email": "alice@example.com", "password": "securepass123"
    })
    assert res.status_code == 200
    assert "session_id" in res.cookies


def test_login_wrong_password(client):
    client.post("/api/auth/signup", json={
        "name": "Alice", "email": "alice@example.com", "password": "securepass123"
    })
    res = client.post("/api/auth/login", json={
        "email": "alice@example.com", "password": "wrongpass"
    })
    assert res.status_code == 401


def test_login_nonexistent_email(client):
    res = client.post("/api/auth/login", json={
        "email": "nobody@example.com", "password": "pass"
    })
    assert res.status_code == 401


def test_me_with_session(client):
    client.post("/api/auth/signup", json={
        "name": "Alice", "email": "alice@example.com", "password": "securepass123"
    })
    res = client.get("/api/auth/me")
    assert res.status_code == 200
    data = res.json()
    assert data["user"]["email"] == "alice@example.com"
    assert data["tenant"]["name"] == "Alice's workspace"


def test_me_without_session(client):
    res = client.get("/api/auth/me")
    assert res.status_code == 401


def test_logout_clears_session(client):
    client.post("/api/auth/signup", json={
        "name": "Alice", "email": "alice@example.com", "password": "securepass123"
    })
    res = client.post("/api/auth/logout")
    assert res.status_code == 200
    res = client.get("/api/auth/me")
    assert res.status_code == 401


def test_google_auth_redirect_not_configured(client):
    """Google auth endpoint should return 501 when GOOGLE_CLIENT_ID is not set."""
    res = client.get("/api/auth/google", follow_redirects=False)
    assert res.status_code == 501
