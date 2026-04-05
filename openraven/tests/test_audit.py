import json
import pytest
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
