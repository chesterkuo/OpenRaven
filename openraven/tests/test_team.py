import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import insert, select

from openraven.auth.db import (
    create_tables, get_engine, invitations, tenants, tenant_members, users,
)


@pytest.fixture
def db_engine(tmp_path):
    engine = get_engine(f"sqlite:///{tmp_path}/test_team.db")
    create_tables(engine)
    return engine


@pytest.fixture
def owner_and_tenant(db_engine):
    user_id = str(uuid.uuid4())
    tenant_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    with db_engine.connect() as conn:
        conn.execute(insert(users).values(
            id=user_id, email="owner@test.com", name="Owner",
            password_hash="$2b$12$fakehash", created_at=now, updated_at=now,
        ))
        conn.execute(insert(tenants).values(
            id=tenant_id, name="Test Tenant", owner_user_id=user_id, created_at=now,
        ))
        conn.execute(insert(tenant_members).values(
            tenant_id=tenant_id, user_id=user_id, role="owner",
        ))
        conn.commit()
    return user_id, tenant_id


@pytest.fixture
def other_user(db_engine):
    user_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    with db_engine.connect() as conn:
        conn.execute(insert(users).values(
            id=user_id, email="member@test.com", name="Member",
            password_hash="$2b$12$fakehash2", created_at=now, updated_at=now,
        ))
        conn.commit()
    return user_id


def test_create_invitation(db_engine, owner_and_tenant):
    from openraven.auth.invitations import create_invitation
    owner_id, tenant_id = owner_and_tenant
    result = create_invitation(db_engine, tenant_id, owner_id)
    assert "token" in result
    assert len(result["token"]) == 32
    assert "id" in result
    assert "expires_at" in result


def test_accept_invitation(db_engine, owner_and_tenant, other_user):
    from openraven.auth.invitations import create_invitation, accept_invitation
    owner_id, tenant_id = owner_and_tenant
    inv = create_invitation(db_engine, tenant_id, owner_id)
    result_tenant_id = accept_invitation(db_engine, inv["token"], other_user)
    assert result_tenant_id == tenant_id
    with db_engine.connect() as conn:
        row = conn.execute(
            select(tenant_members).where(
                tenant_members.c.user_id == other_user,
                tenant_members.c.tenant_id == tenant_id,
            )
        ).first()
    assert row is not None
    assert row.role == "member"


def test_accept_invitation_rejects_expired(db_engine, owner_and_tenant, other_user):
    from openraven.auth.invitations import create_invitation, accept_invitation
    owner_id, tenant_id = owner_and_tenant
    inv = create_invitation(db_engine, tenant_id, owner_id, expires_hours=0)
    with pytest.raises(ValueError, match="expired"):
        accept_invitation(db_engine, inv["token"], other_user)


def test_accept_invitation_rejects_maxed(db_engine, owner_and_tenant, other_user):
    from openraven.auth.invitations import create_invitation, accept_invitation
    owner_id, tenant_id = owner_and_tenant
    inv = create_invitation(db_engine, tenant_id, owner_id, max_uses=0)
    with pytest.raises(ValueError, match="maximum"):
        accept_invitation(db_engine, inv["token"], other_user)


def test_accept_invitation_rejects_duplicate(db_engine, owner_and_tenant):
    from openraven.auth.invitations import create_invitation, accept_invitation
    owner_id, tenant_id = owner_and_tenant
    inv = create_invitation(db_engine, tenant_id, owner_id)
    with pytest.raises(ValueError, match="already"):
        accept_invitation(db_engine, inv["token"], owner_id)


def test_list_invitations(db_engine, owner_and_tenant):
    from openraven.auth.invitations import create_invitation, list_invitations
    owner_id, tenant_id = owner_and_tenant
    create_invitation(db_engine, tenant_id, owner_id)
    create_invitation(db_engine, tenant_id, owner_id)
    result = list_invitations(db_engine, tenant_id)
    assert len(result) == 2


def test_revoke_invitation(db_engine, owner_and_tenant):
    from openraven.auth.invitations import create_invitation, revoke_invitation, list_invitations
    owner_id, tenant_id = owner_and_tenant
    inv = create_invitation(db_engine, tenant_id, owner_id)
    assert revoke_invitation(db_engine, inv["id"], tenant_id) is True
    assert len(list_invitations(db_engine, tenant_id)) == 0


from fastapi.testclient import TestClient


@pytest.fixture
def app_with_team(db_engine, owner_and_tenant):
    from openraven.auth.team_routes import create_team_router
    from openraven.auth.models import AuthContext
    from fastapi import FastAPI, Request
    from starlette.middleware.base import BaseHTTPMiddleware

    owner_id, tenant_id = owner_and_tenant

    app = FastAPI()

    class MockAuthMiddleware(BaseHTTPMiddleware):
        async def dispatch(self, request: Request, call_next):
            request.state.auth = AuthContext(user_id=owner_id, tenant_id=tenant_id, email="owner@test.com")
            return await call_next(request)

    app.add_middleware(MockAuthMiddleware)
    app.include_router(create_team_router(db_engine), prefix="/api/team")
    return app


def test_api_create_invite(app_with_team):
    client = TestClient(app_with_team)
    res = client.post("/api/team/invite")
    assert res.status_code == 200
    data = res.json()
    assert "token" in data
    assert "expires_at" in data


def test_api_list_members(app_with_team):
    client = TestClient(app_with_team)
    res = client.get("/api/team/members")
    assert res.status_code == 200
    data = res.json()
    assert len(data) >= 1
    assert data[0]["role"] == "owner"


def test_api_list_invitations(app_with_team):
    client = TestClient(app_with_team)
    client.post("/api/team/invite")
    client.post("/api/team/invite")
    res = client.get("/api/team/invitations")
    assert res.status_code == 200
    assert len(res.json()) == 2


def test_api_revoke_invitation(app_with_team):
    client = TestClient(app_with_team)
    inv = client.post("/api/team/invite").json()
    res = client.delete(f"/api/team/invitations/{inv['id']}")
    assert res.status_code == 200
    assert client.get("/api/team/invitations").json() == []


def test_api_validate_invite_token(app_with_team):
    client = TestClient(app_with_team)
    inv = client.post("/api/team/invite").json()
    res = client.get(f"/api/team/invite/{inv['token']}")
    assert res.status_code == 200
    assert res.json()["valid"] is True
