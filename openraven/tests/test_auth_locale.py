import pytest
from fastapi.testclient import TestClient
from fastapi import FastAPI
from openraven.auth.db import get_engine, create_tables
from openraven.auth.routes import create_auth_router
import openraven.auth.routes as auth_routes

SUPPORTED_LOCALES = {"en", "zh-TW", "zh-CN", "ja", "ko", "fr", "es", "nl", "it", "vi", "th", "ru"}


@pytest.fixture(autouse=True)
def reset_rate_limiter():
    auth_routes._login_attempts.clear()
    yield
    auth_routes._login_attempts.clear()


@pytest.fixture
def client(tmp_path):
    engine = get_engine(f"sqlite:///{tmp_path}/test_locale.db")
    create_tables(engine)
    app = FastAPI()
    app.include_router(create_auth_router(engine))
    yield TestClient(app)


def _signup_and_login(client) -> TestClient:
    client.post("/api/auth/signup", json={
        "name": "Alice", "email": "alice@example.com", "password": "securepass123"
    })
    return client


def test_me_returns_locale_null_by_default(client):
    _signup_and_login(client)
    res = client.get("/api/auth/me")
    assert res.status_code == 200
    assert res.json()["user"]["locale"] is None


def test_patch_locale_updates_user(client):
    _signup_and_login(client)
    res = client.patch("/api/auth/locale", json={"locale": "zh-TW"})
    assert res.status_code == 200
    assert res.json()["ok"] is True

    me = client.get("/api/auth/me")
    assert me.json()["user"]["locale"] == "zh-TW"


def test_patch_locale_rejects_unsupported(client):
    _signup_and_login(client)
    res = client.patch("/api/auth/locale", json={"locale": "xx-YY"})
    assert res.status_code == 400


def test_patch_locale_requires_auth(client):
    res = client.patch("/api/auth/locale", json={"locale": "en"})
    assert res.status_code == 401
