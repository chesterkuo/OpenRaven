import json
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from openraven.auth.db import audit_logs, create_tables, get_engine


@pytest.fixture
def db_engine(tmp_path):
    engine = get_engine(f"sqlite:///{tmp_path}/test_audit.db")
    create_tables(engine)
    return engine


def test_log_action_inserts_row(db_engine):
    from openraven.audit.logger import log_action
    log_action(
        engine=db_engine,
        user_id="user-1",
        tenant_id="tenant-1",
        action="login",
        details={"method": "email"},
        ip_address="127.0.0.1",
    )
    with db_engine.connect() as conn:
        rows = conn.execute(select(audit_logs)).fetchall()
    assert len(rows) == 1
    row = rows[0]
    assert row.user_id == "user-1"
    assert row.tenant_id == "tenant-1"
    assert row.action == "login"
    assert row.ip_address == "127.0.0.1"
    parsed = json.loads(row.details)
    assert parsed["method"] == "email"


def test_log_action_noop_without_engine():
    from openraven.audit.logger import log_action
    log_action(engine=None, user_id="u1", tenant_id="t1", action="login")


def test_log_action_does_not_raise_on_db_error():
    from openraven.audit.logger import log_action
    from openraven.auth.db import get_engine as _ge
    bad_engine = _ge("sqlite:///nonexistent/path/db.sqlite")
    log_action(engine=bad_engine, user_id="u1", tenant_id="t1", action="login")


def test_log_action_nullable_fields(db_engine):
    from openraven.audit.logger import log_action
    log_action(engine=db_engine, user_id=None, tenant_id="t1", action="system_startup")
    with db_engine.connect() as conn:
        rows = conn.execute(select(audit_logs)).fetchall()
    assert len(rows) == 1
    assert rows[0].user_id is None
    assert rows[0].details is None


def test_query_audit_logs_with_filters(db_engine):
    from openraven.audit.logger import log_action, query_audit_logs
    log_action(engine=db_engine, user_id="u1", tenant_id="t1", action="login")
    log_action(engine=db_engine, user_id="u1", tenant_id="t1", action="file_ingest")
    log_action(engine=db_engine, user_id="u1", tenant_id="t1", action="login")

    all_logs = query_audit_logs(db_engine, tenant_id="t1")
    assert len(all_logs) == 3

    login_only = query_audit_logs(db_engine, tenant_id="t1", action="login")
    assert len(login_only) == 2

    limited = query_audit_logs(db_engine, tenant_id="t1", limit=2)
    assert len(limited) == 2


def test_query_audit_logs_returns_dicts(db_engine):
    from openraven.audit.logger import log_action, query_audit_logs
    log_action(engine=db_engine, user_id="u1", tenant_id="t1", action="kb_query",
               details={"question": "test?"})

    logs = query_audit_logs(db_engine, tenant_id="t1")
    assert len(logs) == 1
    log = logs[0]
    assert log["action"] == "kb_query"
    assert log["user_id"] == "u1"
    assert "timestamp" in log
    assert json.loads(log["details"])["question"] == "test?"


@pytest.fixture
def app_with_audit(db_engine):
    """Create a FastAPI app with audit routes, mocking auth context."""
    from openraven.audit.routes import create_audit_router
    from openraven.auth.models import AuthContext
    from fastapi import FastAPI, Request
    from starlette.middleware.base import BaseHTTPMiddleware

    app = FastAPI()

    class MockAuthMiddleware(BaseHTTPMiddleware):
        async def dispatch(self, request: Request, call_next):
            request.state.auth = AuthContext(user_id="u1", tenant_id="t1", email="u1@test.com")
            return await call_next(request)

    app.add_middleware(MockAuthMiddleware)
    app.include_router(create_audit_router(db_engine), prefix="/api/audit")

    from openraven.audit.logger import log_action
    log_action(engine=db_engine, user_id="u1", tenant_id="t1", action="login", ip_address="1.2.3.4")
    log_action(engine=db_engine, user_id="u1", tenant_id="t1", action="file_ingest",
               details={"files": ["report.pdf"]})
    log_action(engine=db_engine, user_id="u2", tenant_id="t1", action="kb_query",
               details={"question": "test?"})

    return app


def test_audit_list_returns_logs(app_with_audit):
    client = TestClient(app_with_audit)
    res = client.get("/api/audit/")
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 3
    assert len(data["logs"]) == 3


def test_audit_list_filters_by_action(app_with_audit):
    client = TestClient(app_with_audit)
    res = client.get("/api/audit/?action=login")
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 1
    assert all(log["action"] == "login" for log in data["logs"])


def test_audit_list_pagination(app_with_audit):
    client = TestClient(app_with_audit)
    res = client.get("/api/audit/?limit=2&offset=0")
    assert res.status_code == 200
    data = res.json()
    assert len(data["logs"]) == 2
    assert data["total"] == 3


def test_audit_export_csv(app_with_audit):
    client = TestClient(app_with_audit)
    res = client.get("/api/audit/export")
    assert res.status_code == 200
    assert "text/csv" in res.headers["content-type"]
    lines = res.text.strip().split("\n")
    assert len(lines) == 4  # header + 3 data rows
    assert "action" in lines[0]
