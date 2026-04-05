import json
import uuid
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import pytest
from sqlalchemy import insert, select

from openraven.auth.db import (
    create_tables, get_engine, users, tenants, tenant_members, sessions,
    audit_logs, invitations,
)


@pytest.fixture
def db_engine(tmp_path):
    engine = get_engine(f"sqlite:///{tmp_path}/test_account.db")
    create_tables(engine)
    return engine


@pytest.fixture
def sole_owner(db_engine, tmp_path):
    user_id = str(uuid.uuid4())
    tenant_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    with db_engine.connect() as conn:
        conn.execute(insert(users).values(
            id=user_id, email="sole@test.com", name="Sole Owner",
            password_hash="$2b$12$fakehash", created_at=now, updated_at=now,
        ))
        conn.execute(insert(tenants).values(
            id=tenant_id, name="Test Tenant", owner_user_id=user_id, created_at=now,
        ))
        conn.execute(insert(tenant_members).values(
            tenant_id=tenant_id, user_id=user_id, role="owner",
        ))
        conn.execute(insert(audit_logs).values(
            user_id=user_id, tenant_id=tenant_id, action="login", timestamp=now,
        ))
        conn.commit()
    data_dir = tmp_path / "tenants" / tenant_id
    wiki_dir = data_dir / "wiki"
    wiki_dir.mkdir(parents=True)
    (wiki_dir / "article1.md").write_text("# Article 1\nContent here.")
    (wiki_dir / "article2.md").write_text("# Article 2\nMore content.")
    return user_id, tenant_id, data_dir


@pytest.fixture
def owner_with_members(db_engine, tmp_path):
    owner_id = str(uuid.uuid4())
    member_id = str(uuid.uuid4())
    tenant_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    with db_engine.connect() as conn:
        conn.execute(insert(users).values(
            id=owner_id, email="owner@test.com", name="Owner",
            password_hash="$2b$12$fakehash", created_at=now, updated_at=now,
        ))
        conn.execute(insert(users).values(
            id=member_id, email="member@test.com", name="Member",
            password_hash="$2b$12$fakehash2", created_at=now, updated_at=now,
        ))
        conn.execute(insert(tenants).values(
            id=tenant_id, name="Team Tenant", owner_user_id=owner_id, created_at=now,
        ))
        conn.execute(insert(tenant_members).values(
            tenant_id=tenant_id, user_id=owner_id, role="owner",
        ))
        conn.execute(insert(tenant_members).values(
            tenant_id=tenant_id, user_id=member_id, role="member",
        ))
        conn.commit()
    return owner_id, member_id, tenant_id


def test_check_eligible_sole_owner(db_engine, sole_owner):
    from openraven.auth.account import check_deletion_eligibility
    user_id, tenant_id, _ = sole_owner
    result = check_deletion_eligibility(db_engine, user_id)
    assert result["eligible"] is True
    assert result["tenant_id"] == tenant_id
    assert result["member_count"] == 1


def test_check_blocked_with_members(db_engine, owner_with_members):
    from openraven.auth.account import check_deletion_eligibility
    owner_id, _, _ = owner_with_members
    result = check_deletion_eligibility(db_engine, owner_id)
    assert result["eligible"] is False
    assert "member" in result["reason"].lower()
    assert result["member_count"] == 2


def test_delete_account_removes_all(db_engine, sole_owner):
    from openraven.auth.account import delete_account
    user_id, tenant_id, data_dir = sole_owner
    delete_account(db_engine, user_id, tenant_id, data_dir)
    with db_engine.connect() as conn:
        assert conn.execute(select(users).where(users.c.id == user_id)).first() is None
        assert conn.execute(select(tenants).where(tenants.c.id == tenant_id)).first() is None
        assert conn.execute(select(tenant_members).where(tenant_members.c.tenant_id == tenant_id)).first() is None
        assert conn.execute(select(audit_logs).where(audit_logs.c.tenant_id == tenant_id)).first() is None
    assert not data_dir.exists()


def test_delete_account_skips_missing_dir(db_engine, sole_owner):
    from openraven.auth.account import delete_account
    user_id, tenant_id, data_dir = sole_owner
    import shutil
    shutil.rmtree(data_dir)
    delete_account(db_engine, user_id, tenant_id, data_dir)


def test_export_knowledge_base(sole_owner, tmp_path):
    _, tenant_id, data_dir = sole_owner
    from openraven.auth.account import export_knowledge_base
    zip_path = export_knowledge_base(data_dir, tmp_path / "export")
    assert zip_path.exists()
    assert zip_path.suffix == ".zip"
    with zipfile.ZipFile(zip_path) as zf:
        names = zf.namelist()
        assert "article1.md" in names
        assert "article2.md" in names
        assert "metadata.json" in names
        meta = json.loads(zf.read("metadata.json"))
        assert meta["file_count"] == 2
