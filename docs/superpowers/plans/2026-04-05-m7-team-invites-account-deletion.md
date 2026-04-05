# M7.2 Team Invites + M7.9 Account Deletion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let tenant owners invite members via shareable links, and let users export their KB and permanently delete their account. Both features live in a unified Settings page.

**Architecture:** New `invitations` table + `invitations.py` module for team invites. New `account.py` module for deletion + export. New `SettingsPage.tsx` with Team/Account tabs. All endpoints tenant-scoped via `request.state.auth`.

**Tech Stack:** Python 3.12, SQLAlchemy, Alembic, FastAPI, React 19 + TypeScript

---

## File Structure

| File | Action | Responsibility |
|------|--------|---------------|
| `openraven/src/openraven/auth/db.py` | Modify | Add `invitations` table |
| `openraven/alembic/versions/004_invitations.py` | Create | Migration for invitations table |
| `openraven/src/openraven/auth/invitations.py` | Create | Invite CRUD: create, accept, list, revoke |
| `openraven/src/openraven/auth/account.py` | Create | Eligibility check, delete, KB export |
| `openraven/src/openraven/auth/team_routes.py` | Create | /api/team/* endpoints |
| `openraven/src/openraven/auth/account_routes.py` | Create | /api/account/* endpoints |
| `openraven/src/openraven/api/server.py` | Modify | Register team + account routers |
| `openraven/tests/test_team.py` | Create | Team invite tests |
| `openraven/tests/test_account.py` | Create | Account deletion + export tests |
| `openraven-ui/src/pages/SettingsPage.tsx` | Create | Settings page with Team + Account tabs |
| `openraven-ui/src/App.tsx` | Modify | Add /settings route, nav link |
| `openraven-ui/server/index.ts` | Modify | Add BFF proxy for /api/team, /api/account |
| `openraven-ui/public/locales/en/common.json` | Modify | Add nav.settings i18n key |

---

## Task 1: Invitations Database Schema

**Files:**
- Modify: `openraven/src/openraven/auth/db.py`
- Create: `openraven/alembic/versions/004_invitations.py`

- [ ] **Step 1: Add invitations table to db.py**

In `openraven/src/openraven/auth/db.py`, add after the `audit_logs` table and before `get_engine`:

```python
invitations = Table(
    "invitations", metadata,
    Column("id", String(36), primary_key=True),
    Column("tenant_id", String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
    Column("token", String(64), unique=True, nullable=False),
    Column("created_by", String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
    Column("expires_at", DateTime(timezone=True), nullable=False),
    Column("max_uses", Integer, nullable=True),
    Column("use_count", Integer, nullable=False, default=0),
    Column("created_at", DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)),
)
```

- [ ] **Step 2: Create Alembic migration**

Create `openraven/alembic/versions/004_invitations.py`:

```python
"""Invitations table for team invite links.

Revision ID: 004
Create Date: 2026-04-05
"""
from alembic import op
import sqlalchemy as sa

revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "invitations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(36), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("token", sa.String(64), unique=True, nullable=False),
        sa.Column("created_by", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("max_uses", sa.Integer, nullable=True),
        sa.Column("use_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("invitations")
```

- [ ] **Step 3: Verify tables create**

```bash
cd /home/ubuntu/source/OpenRaven/openraven && python3 -c "
from openraven.auth.db import get_engine, create_tables
from sqlalchemy import inspect
engine = get_engine('sqlite:///test_inv.db')
create_tables(engine)
tables = inspect(engine).get_table_names()
assert 'invitations' in tables, f'invitations not found in {tables}'
print(f'Tables: {tables}')
import os; os.remove('test_inv.db')
print('OK')
"
```

- [ ] **Step 4: Commit**

```bash
cd /home/ubuntu/source/OpenRaven && git add openraven/src/openraven/auth/db.py openraven/alembic/versions/004_invitations.py && git commit -m "$(cat <<'EOF'
feat(m7): add invitations table and Alembic migration 004

New invitations table with tenant_id, token (unique 64-char),
created_by, expires_at, max_uses, use_count for team invite links.

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 2: Invitations Module

**Files:**
- Create: `openraven/src/openraven/auth/invitations.py`
- Create: `openraven/tests/test_team.py`

- [ ] **Step 1: Write failing tests**

Create `openraven/tests/test_team.py`:

```python
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
    """Create an owner user and their tenant."""
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
    """Create a second user (not in any tenant)."""
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

    # Verify user is now a tenant member
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

    # Owner is already a member
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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /home/ubuntu/source/OpenRaven/openraven && python3 -m pytest tests/test_team.py -v 2>&1 | tail -10
```

- [ ] **Step 3: Implement invitations.py**

Create `openraven/src/openraven/auth/invitations.py`:

```python
"""Team invitation management — create, accept, list, revoke invite links."""
from __future__ import annotations

import secrets
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import insert, select, update, delete
from sqlalchemy.engine import Engine

from openraven.auth.db import invitations, tenant_members


def create_invitation(
    engine: Engine,
    tenant_id: str,
    created_by: str,
    expires_hours: int = 48,
    max_uses: int | None = None,
) -> dict:
    """Create a new invitation link. Returns {id, token, expires_at}."""
    inv_id = str(uuid.uuid4())
    token = secrets.token_hex(16)  # 32-char hex
    expires_at = datetime.now(timezone.utc) + timedelta(hours=expires_hours)

    with engine.connect() as conn:
        conn.execute(insert(invitations).values(
            id=inv_id,
            tenant_id=tenant_id,
            token=token,
            created_by=created_by,
            expires_at=expires_at,
            max_uses=max_uses,
            use_count=0,
        ))
        conn.commit()

    return {"id": inv_id, "token": token, "expires_at": expires_at.isoformat()}


def accept_invitation(engine: Engine, token: str, user_id: str) -> str:
    """Accept an invitation. Returns tenant_id. Raises ValueError on failure."""
    with engine.connect() as conn:
        row = conn.execute(
            select(invitations).where(invitations.c.token == token)
        ).first()

        if not row:
            raise ValueError("Invitation not found")

        now = datetime.now(timezone.utc)
        if row.expires_at.replace(tzinfo=timezone.utc) < now:
            raise ValueError("Invitation has expired")

        if row.max_uses is not None and row.use_count >= row.max_uses:
            raise ValueError("Invitation has reached its maximum uses")

        # Check if user is already a member
        existing = conn.execute(
            select(tenant_members).where(
                tenant_members.c.tenant_id == row.tenant_id,
                tenant_members.c.user_id == user_id,
            )
        ).first()
        if existing:
            raise ValueError("User is already a member of this tenant")

        # Add user as member
        conn.execute(insert(tenant_members).values(
            tenant_id=row.tenant_id,
            user_id=user_id,
            role="member",
        ))

        # Increment use count
        conn.execute(
            update(invitations)
            .where(invitations.c.id == row.id)
            .values(use_count=row.use_count + 1)
        )
        conn.commit()

    return row.tenant_id


def list_invitations(engine: Engine, tenant_id: str) -> list[dict]:
    """List active (non-expired) invitations for a tenant."""
    now = datetime.now(timezone.utc)
    with engine.connect() as conn:
        rows = conn.execute(
            select(invitations)
            .where(invitations.c.tenant_id == tenant_id)
            .where(invitations.c.expires_at > now)
            .order_by(invitations.c.created_at.desc())
        ).fetchall()

    return [
        {
            "id": row.id,
            "token": row.token,
            "expires_at": row.expires_at.isoformat() if row.expires_at else None,
            "max_uses": row.max_uses,
            "use_count": row.use_count,
            "created_at": row.created_at.isoformat() if row.created_at else None,
        }
        for row in rows
    ]


def revoke_invitation(engine: Engine, invitation_id: str, tenant_id: str) -> bool:
    """Delete an invitation. Returns True if deleted, False if not found."""
    with engine.connect() as conn:
        result = conn.execute(
            delete(invitations).where(
                invitations.c.id == invitation_id,
                invitations.c.tenant_id == tenant_id,
            )
        )
        conn.commit()
    return result.rowcount > 0
```

- [ ] **Step 4: Run tests**

```bash
cd /home/ubuntu/source/OpenRaven/openraven && python3 -m pytest tests/test_team.py -v 2>&1 | tail -15
```
Expected: All 7 tests PASS.

- [ ] **Step 5: Commit**

```bash
cd /home/ubuntu/source/OpenRaven && git add openraven/src/openraven/auth/invitations.py openraven/tests/test_team.py && git commit -m "$(cat <<'EOF'
feat(m7): add team invitation module with create, accept, list, revoke

Shareable invite links with 32-char hex tokens, 48h expiry, optional
max_uses. Accept adds user as tenant member. 7 tests.

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 3: Team API Routes

**Files:**
- Create: `openraven/src/openraven/auth/team_routes.py`
- Modify: `openraven/tests/test_team.py`

- [ ] **Step 1: Add API tests**

Append to `openraven/tests/test_team.py`:

```python
from fastapi.testclient import TestClient


@pytest.fixture
def app_with_team(db_engine, owner_and_tenant):
    """Create a FastAPI app with team routes, mocking auth as owner."""
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
```

- [ ] **Step 2: Implement team_routes.py**

Create `openraven/src/openraven/auth/team_routes.py`:

```python
"""Team management API routes."""
from __future__ import annotations

from fastapi import APIRouter, Request, HTTPException
from sqlalchemy import select
from sqlalchemy.engine import Engine

from openraven.auth.db import tenants, tenant_members, users
from openraven.auth.invitations import (
    create_invitation, accept_invitation, list_invitations, revoke_invitation,
)


def create_team_router(engine: Engine) -> APIRouter:
    router = APIRouter()

    def _require_owner(request: Request) -> tuple[str, str]:
        """Return (user_id, tenant_id). Raise 403 if not tenant owner."""
        auth = getattr(request.state, "auth", None)
        if not auth:
            raise HTTPException(401, "Not authenticated")
        with engine.connect() as conn:
            row = conn.execute(
                select(tenants.c.owner_user_id).where(tenants.c.id == auth.tenant_id)
            ).first()
        if not row or row.owner_user_id != auth.user_id:
            raise HTTPException(403, "Only the tenant owner can perform this action")
        return auth.user_id, auth.tenant_id

    def _get_auth(request: Request) -> tuple[str, str]:
        """Return (user_id, tenant_id). Raise 401 if not authenticated."""
        auth = getattr(request.state, "auth", None)
        if not auth:
            raise HTTPException(401, "Not authenticated")
        return auth.user_id, auth.tenant_id

    @router.post("/invite")
    async def create_invite(request: Request):
        user_id, tenant_id = _require_owner(request)
        result = create_invitation(engine, tenant_id, user_id)
        return result

    @router.get("/invite/{token}")
    async def validate_invite(token: str):
        """Check if an invite token is valid. Public endpoint."""
        from openraven.auth.db import invitations
        from datetime import datetime, timezone
        with engine.connect() as conn:
            row = conn.execute(
                select(invitations).where(invitations.c.token == token)
            ).first()
        if not row:
            return {"valid": False, "reason": "not_found"}
        now = datetime.now(timezone.utc)
        if row.expires_at.replace(tzinfo=timezone.utc) < now:
            return {"valid": False, "reason": "expired"}
        if row.max_uses is not None and row.use_count >= row.max_uses:
            return {"valid": False, "reason": "maxed"}
        # Get tenant name
        with engine.connect() as conn:
            tenant = conn.execute(
                select(tenants.c.name).where(tenants.c.id == row.tenant_id)
            ).first()
        return {"valid": True, "tenant_name": tenant.name if tenant else "Unknown"}

    @router.post("/invite/{token}/accept")
    async def accept_invite(token: str, request: Request):
        user_id, _ = _get_auth(request)
        try:
            tenant_id = accept_invitation(engine, token, user_id)
            return {"tenant_id": tenant_id, "accepted": True}
        except ValueError as e:
            raise HTTPException(400, str(e))

    @router.get("/members")
    async def list_members(request: Request):
        _, tenant_id = _get_auth(request)
        with engine.connect() as conn:
            rows = conn.execute(
                select(
                    tenant_members.c.user_id,
                    tenant_members.c.role,
                    users.c.email,
                    users.c.name,
                    users.c.created_at,
                )
                .join(users, tenant_members.c.user_id == users.c.id)
                .where(tenant_members.c.tenant_id == tenant_id)
            ).fetchall()
        return [
            {
                "user_id": row.user_id,
                "email": row.email,
                "name": row.name,
                "role": row.role,
                "joined_at": row.created_at.isoformat() if row.created_at else None,
            }
            for row in rows
        ]

    @router.delete("/members/{user_id}")
    async def remove_member(user_id: str, request: Request):
        owner_id, tenant_id = _require_owner(request)
        if user_id == owner_id:
            raise HTTPException(400, "Cannot remove yourself as owner")
        from sqlalchemy import delete
        with engine.connect() as conn:
            result = conn.execute(
                delete(tenant_members).where(
                    tenant_members.c.tenant_id == tenant_id,
                    tenant_members.c.user_id == user_id,
                )
            )
            conn.commit()
        if result.rowcount == 0:
            raise HTTPException(404, "Member not found")
        return {"removed": True}

    @router.get("/invitations")
    async def get_invitations(request: Request):
        _require_owner(request)
        _, tenant_id = _get_auth(request)
        return list_invitations(engine, tenant_id)

    @router.delete("/invitations/{invitation_id}")
    async def delete_invitation(invitation_id: str, request: Request):
        _, tenant_id = _require_owner(request)
        if not revoke_invitation(engine, invitation_id, tenant_id):
            raise HTTPException(404, "Invitation not found")
        return {"revoked": True}

    return router
```

- [ ] **Step 3: Run tests**

```bash
cd /home/ubuntu/source/OpenRaven/openraven && python3 -m pytest tests/test_team.py -v 2>&1 | tail -20
```
Expected: All 12 tests PASS.

- [ ] **Step 4: Commit**

```bash
cd /home/ubuntu/source/OpenRaven && git add openraven/src/openraven/auth/team_routes.py openraven/tests/test_team.py && git commit -m "$(cat <<'EOF'
feat(m7): add team API routes — invite, accept, members, revoke

POST /api/team/invite (owner), GET /invite/{token} (public),
POST /invite/{token}/accept (auth), GET /members, DELETE /members/{id},
GET /invitations, DELETE /invitations/{id}. Owner-only checks.

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 4: Account Deletion & Export Module

**Files:**
- Create: `openraven/src/openraven/auth/account.py`
- Create: `openraven/tests/test_account.py`

- [ ] **Step 1: Write failing tests**

Create `openraven/tests/test_account.py`:

```python
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
    """Create a sole owner with a tenant and some data."""
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

    # Create tenant data directory with wiki files
    data_dir = tmp_path / "tenants" / tenant_id
    wiki_dir = data_dir / "wiki"
    wiki_dir.mkdir(parents=True)
    (wiki_dir / "article1.md").write_text("# Article 1\nContent here.")
    (wiki_dir / "article2.md").write_text("# Article 2\nMore content.")

    return user_id, tenant_id, data_dir


@pytest.fixture
def owner_with_members(db_engine, tmp_path):
    """Create an owner with a tenant that has other members."""
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

    # Data directory should be removed
    assert not data_dir.exists()


def test_delete_account_skips_missing_dir(db_engine, sole_owner):
    """Should not crash if data directory doesn't exist."""
    from openraven.auth.account import delete_account
    user_id, tenant_id, data_dir = sole_owner
    import shutil
    shutil.rmtree(data_dir)
    delete_account(db_engine, user_id, tenant_id, data_dir)  # Should not raise


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
```

- [ ] **Step 2: Implement account.py**

Create `openraven/src/openraven/auth/account.py`:

```python
"""Account deletion and knowledge base export."""
from __future__ import annotations

import json
import logging
import shutil
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import delete, select, func
from sqlalchemy.engine import Engine

from openraven.auth.db import (
    users, sessions, tenants, tenant_members, audit_logs,
    invitations, password_reset_tokens,
)

logger = logging.getLogger(__name__)


def check_deletion_eligibility(engine: Engine, user_id: str) -> dict:
    """Check if user can delete their account.

    Returns {eligible, reason, tenant_id, member_count}.
    Blocked if user is tenant owner with other members.
    """
    with engine.connect() as conn:
        # Find user's tenant (as owner)
        tenant_row = conn.execute(
            select(tenants.c.id).where(tenants.c.owner_user_id == user_id)
        ).first()

        if not tenant_row:
            # User is not an owner — can always delete
            return {"eligible": True, "reason": "", "tenant_id": None, "member_count": 0}

        tenant_id = tenant_row.id

        # Count members
        member_count = conn.execute(
            select(func.count()).select_from(tenant_members)
            .where(tenant_members.c.tenant_id == tenant_id)
        ).scalar() or 0

        if member_count > 1:
            return {
                "eligible": False,
                "reason": f"Remove all {member_count - 1} team member(s) before deleting your account",
                "tenant_id": tenant_id,
                "member_count": member_count,
            }

        return {
            "eligible": True,
            "reason": "",
            "tenant_id": tenant_id,
            "member_count": member_count,
        }


def delete_account(
    engine: Engine,
    user_id: str,
    tenant_id: str | None,
    data_dir: Path,
) -> None:
    """Permanently delete a user account and all associated data.

    Deletion order matters to respect foreign key constraints:
    1. Files on disk
    2. audit_logs, invitations (reference tenant)
    3. tenant_members (reference tenant + user)
    4. tenants (reference user as owner)
    5. sessions, password_reset_tokens (reference user)
    6. users
    """
    # 1. Remove tenant data directory
    if data_dir.exists():
        shutil.rmtree(data_dir, ignore_errors=True)

    with engine.connect() as conn:
        if tenant_id:
            # 2. Remove tenant-scoped records
            conn.execute(delete(audit_logs).where(audit_logs.c.tenant_id == tenant_id))
            conn.execute(delete(invitations).where(invitations.c.tenant_id == tenant_id))
            # 3. Remove tenant memberships
            conn.execute(delete(tenant_members).where(tenant_members.c.tenant_id == tenant_id))
            # 4. Remove tenant
            conn.execute(delete(tenants).where(tenants.c.id == tenant_id))

        # 5. Remove user sessions and tokens
        conn.execute(delete(sessions).where(sessions.c.user_id == user_id))
        conn.execute(delete(password_reset_tokens).where(password_reset_tokens.c.user_id == user_id))
        # Also remove user from any other tenants they're a member of
        conn.execute(delete(tenant_members).where(tenant_members.c.user_id == user_id))
        # 6. Remove user
        conn.execute(delete(users).where(users.c.id == user_id))

        conn.commit()

    logger.info(f"Account deleted: user_id={user_id}, tenant_id={tenant_id}")


def export_knowledge_base(data_dir: Path, output_dir: Path) -> Path:
    """Create a zip export of the knowledge base.

    Includes wiki articles, GraphML export, and metadata.
    Returns path to the created zip file.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    zip_path = output_dir / "openraven_export.zip"

    wiki_dir = data_dir / "wiki"
    graphml_path = data_dir / "lightrag_data" / "graph_chunk_entity_relation.graphml"

    file_count = 0
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        # Wiki articles
        if wiki_dir.exists():
            for f in sorted(wiki_dir.glob("*.md")):
                zf.write(f, f.name)
                file_count += 1

        # GraphML
        if graphml_path.exists():
            zf.write(graphml_path, "knowledge_graph.graphml")

        # Metadata
        meta = {
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "file_count": file_count,
        }
        zf.writestr("metadata.json", json.dumps(meta, indent=2))

    return zip_path
```

- [ ] **Step 3: Run tests**

```bash
cd /home/ubuntu/source/OpenRaven/openraven && python3 -m pytest tests/test_account.py -v 2>&1 | tail -15
```
Expected: All 5 tests PASS.

- [ ] **Step 4: Commit**

```bash
cd /home/ubuntu/source/OpenRaven && git add openraven/src/openraven/auth/account.py openraven/tests/test_account.py && git commit -m "$(cat <<'EOF'
feat(m7): add account deletion and KB export module

check_deletion_eligibility() blocks if owner with members.
delete_account() cascading delete: files → DB records → user.
export_knowledge_base() creates zip with wiki + graphml + metadata.

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 5: Account API Routes

**Files:**
- Create: `openraven/src/openraven/auth/account_routes.py`
- Modify: `openraven/tests/test_account.py`

- [ ] **Step 1: Add API tests**

Append to `openraven/tests/test_account.py`:

```python
from fastapi.testclient import TestClient
from openraven.auth.passwords import hash_password


@pytest.fixture
def sole_owner_with_real_password(db_engine, tmp_path):
    """Owner with a real bcrypt password for API testing."""
    user_id = str(uuid.uuid4())
    tenant_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    pw_hash = hash_password("mypassword123")

    with db_engine.connect() as conn:
        conn.execute(insert(users).values(
            id=user_id, email="api@test.com", name="API User",
            password_hash=pw_hash, created_at=now, updated_at=now,
        ))
        conn.execute(insert(tenants).values(
            id=tenant_id, name="API Tenant", owner_user_id=user_id, created_at=now,
        ))
        conn.execute(insert(tenant_members).values(
            tenant_id=tenant_id, user_id=user_id, role="owner",
        ))
        conn.commit()

    data_dir = tmp_path / "tenants" / tenant_id
    wiki_dir = data_dir / "wiki"
    wiki_dir.mkdir(parents=True)
    (wiki_dir / "test.md").write_text("# Test")

    return user_id, tenant_id, data_dir, pw_hash


@pytest.fixture
def app_with_account(db_engine, sole_owner_with_real_password, tmp_path):
    from openraven.auth.account_routes import create_account_router
    from openraven.auth.models import AuthContext
    from fastapi import FastAPI, Request
    from starlette.middleware.base import BaseHTTPMiddleware

    user_id, tenant_id, data_dir, _ = sole_owner_with_real_password

    app = FastAPI()

    class MockAuthMiddleware(BaseHTTPMiddleware):
        async def dispatch(self, request: Request, call_next):
            request.state.auth = AuthContext(user_id=user_id, tenant_id=tenant_id, email="api@test.com")
            return await call_next(request)

    app.add_middleware(MockAuthMiddleware)
    app.include_router(create_account_router(db_engine, data_root=tmp_path / "tenants"), prefix="/api/account")
    return app


def test_api_account_info(app_with_account):
    client = TestClient(app_with_account)
    res = client.get("/api/account/")
    assert res.status_code == 200
    data = res.json()
    assert data["email"] == "api@test.com"
    assert data["deletion"]["eligible"] is True


def test_api_export_kb(app_with_account):
    client = TestClient(app_with_account)
    res = client.get("/api/account/export")
    assert res.status_code == 200
    assert "application/zip" in res.headers.get("content-type", "") or "application/x-zip" in res.headers.get("content-type", "")


def test_api_delete_account_wrong_password(app_with_account):
    client = TestClient(app_with_account)
    res = client.request("DELETE", "/api/account/", json={"password": "wrongpassword"})
    assert res.status_code == 403


def test_api_delete_account_correct_password(app_with_account, db_engine, sole_owner_with_real_password):
    user_id, tenant_id, _, _ = sole_owner_with_real_password
    client = TestClient(app_with_account)
    res = client.request("DELETE", "/api/account/", json={"password": "mypassword123"})
    assert res.status_code == 200
    assert res.json()["deleted"] is True

    # Verify user is gone
    with db_engine.connect() as conn:
        assert conn.execute(select(users).where(users.c.id == user_id)).first() is None
```

- [ ] **Step 2: Implement account_routes.py**

Create `openraven/src/openraven/auth/account_routes.py`:

```python
"""Account management API routes — info, export, delete."""
from __future__ import annotations

import tempfile
from pathlib import Path

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.engine import Engine

from openraven.auth.db import users
from openraven.auth.account import (
    check_deletion_eligibility, delete_account, export_knowledge_base,
)
from openraven.auth.passwords import verify_password


class DeleteRequest(BaseModel):
    password: str


def create_account_router(engine: Engine, data_root: Path = Path("/data/tenants")) -> APIRouter:
    router = APIRouter()

    def _get_auth(request: Request):
        auth = getattr(request.state, "auth", None)
        if not auth:
            raise HTTPException(401, "Not authenticated")
        return auth

    @router.get("/")
    async def account_info(request: Request):
        auth = _get_auth(request)
        with engine.connect() as conn:
            user = conn.execute(
                select(users).where(users.c.id == auth.user_id)
            ).first()
        if not user:
            raise HTTPException(404, "User not found")

        eligibility = check_deletion_eligibility(engine, auth.user_id)

        return {
            "user_id": user.id,
            "email": user.email,
            "name": user.name,
            "created_at": user.created_at.isoformat() if user.created_at else None,
            "deletion": eligibility,
        }

    @router.get("/export")
    async def export_kb(request: Request):
        auth = _get_auth(request)
        data_dir = data_root / auth.tenant_id
        if not data_dir.exists():
            raise HTTPException(404, "No knowledge base data found")

        import os
        export_dir = Path(tempfile.mkdtemp())
        zip_path = export_knowledge_base(data_dir, export_dir)

        return FileResponse(
            path=str(zip_path),
            media_type="application/zip",
            filename="openraven_export.zip",
            background=None,  # Don't delete until response is sent
        )

    @router.delete("/")
    async def delete_my_account(request: Request, body: DeleteRequest):
        auth = _get_auth(request)

        # Verify password
        with engine.connect() as conn:
            user = conn.execute(
                select(users.c.password_hash).where(users.c.id == auth.user_id)
            ).first()
        if not user or not user.password_hash:
            raise HTTPException(400, "Cannot verify password (OAuth-only account)")
        if not verify_password(body.password, user.password_hash):
            raise HTTPException(403, "Incorrect password")

        # Check eligibility
        eligibility = check_deletion_eligibility(engine, auth.user_id)
        if not eligibility["eligible"]:
            raise HTTPException(400, eligibility["reason"])

        # Delete
        data_dir = data_root / auth.tenant_id
        delete_account(engine, auth.user_id, eligibility["tenant_id"], data_dir)

        return {"deleted": True}

    return router
```

- [ ] **Step 3: Run tests**

```bash
cd /home/ubuntu/source/OpenRaven/openraven && python3 -m pytest tests/test_account.py -v 2>&1 | tail -15
```
Expected: All 9 tests PASS.

- [ ] **Step 4: Commit**

```bash
cd /home/ubuntu/source/OpenRaven && git add openraven/src/openraven/auth/account_routes.py openraven/tests/test_account.py && git commit -m "$(cat <<'EOF'
feat(m7): add account API routes — info, export, delete

GET /api/account (info + eligibility), GET /api/account/export (zip),
DELETE /api/account (password required, checks eligibility first).

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 6: Register Routes in Server + Auth Middleware

**Files:**
- Modify: `openraven/src/openraven/api/server.py`

- [ ] **Step 1: Register team + account routers**

In `openraven/src/openraven/api/server.py`, inside the `if config.auth_enabled:` block (after the audit router registration around line 128), add:

```python
        from openraven.auth.team_routes import create_team_router
        from openraven.auth.account_routes import create_account_router
        app.include_router(create_team_router(auth_engine), prefix="/api/team", tags=["team"])
        app.include_router(create_account_router(auth_engine), prefix="/api/account", tags=["account"])
```

- [ ] **Step 2: Update auth middleware to allow public invite validation**

In the `AuthMiddleware.dispatch` method, the public endpoint skip list currently has:
```python
if (path.startswith("/api/auth/") or path == "/health"
        or path.startswith("/agents/")):
```
Add the public invite validation endpoint:
```python
if (path.startswith("/api/auth/") or path == "/health"
        or path.startswith("/agents/")
        or (path.startswith("/api/team/invite/") and request.method == "GET")):
```

- [ ] **Step 3: Run tests**

```bash
cd /home/ubuntu/source/OpenRaven/openraven && python3 -m pytest tests/test_team.py tests/test_account.py tests/test_api.py -v 2>&1 | tail -20
```
Expected: All tests PASS.

- [ ] **Step 4: Commit**

```bash
cd /home/ubuntu/source/OpenRaven && git add openraven/src/openraven/api/server.py && git commit -m "$(cat <<'EOF'
feat(m7): register team and account routers in server

/api/team/* and /api/account/* routes active when DATABASE_URL is set.
GET /api/team/invite/{token} is public (no auth required).

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 7: Settings Page UI

**Files:**
- Create: `openraven-ui/src/pages/SettingsPage.tsx`
- Modify: `openraven-ui/src/App.tsx`
- Modify: `openraven-ui/public/locales/en/common.json`

- [ ] **Step 1: Create SettingsPage component**

Create `openraven-ui/src/pages/SettingsPage.tsx`:

```tsx
import { useEffect, useState } from "react";

interface Member { user_id: string; email: string; name: string; role: string; joined_at: string | null; }
interface Invitation { id: string; token: string; expires_at: string | null; max_uses: number | null; use_count: number; }
interface AccountInfo { user_id: string; email: string; name: string; created_at: string | null; deletion: { eligible: boolean; reason: string; member_count: number; }; }

export default function SettingsPage() {
  const [tab, setTab] = useState<"team" | "account">("team");

  return (
    <div>
      <h1 className="text-3xl mb-6" style={{ color: "var(--color-text)", lineHeight: 1.15 }}>Settings</h1>
      <div className="flex gap-4 mb-8" style={{ borderBottom: "2px solid var(--color-border)" }}>
        {(["team", "account"] as const).map(t => (
          <button key={t} onClick={() => setTab(t)}
            className="px-4 py-2 text-sm cursor-pointer capitalize"
            style={{
              color: tab === t ? "var(--color-brand)" : "var(--color-text-muted)",
              borderBottom: tab === t ? "2px solid var(--color-brand)" : "2px solid transparent",
              background: "transparent", marginBottom: "-2px",
            }}
          >{t}</button>
        ))}
      </div>
      {tab === "team" && <TeamTab />}
      {tab === "account" && <AccountTab />}
    </div>
  );
}

function TeamTab() {
  const [members, setMembers] = useState<Member[]>([]);
  const [invitations, setInvitations] = useState<Invitation[]>([]);
  const [inviteLink, setInviteLink] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetch("/api/team/members").then(r => r.json()).then(setMembers).catch(() => {});
    fetch("/api/team/invitations").then(r => r.json()).then(setInvitations).catch(() => {});
  }, []);

  async function createInvite() {
    setLoading(true);
    try {
      const res = await fetch("/api/team/invite", { method: "POST" });
      const data = await res.json();
      setInviteLink(`${window.location.origin}/invite/${data.token}`);
      // Refresh invitations
      const inv = await fetch("/api/team/invitations").then(r => r.json());
      setInvitations(inv);
    } finally { setLoading(false); }
  }

  async function removeMember(userId: string) {
    await fetch(`/api/team/members/${userId}`, { method: "DELETE" });
    setMembers(prev => prev.filter(m => m.user_id !== userId));
  }

  async function revokeInvitation(id: string) {
    await fetch(`/api/team/invitations/${id}`, { method: "DELETE" });
    setInvitations(prev => prev.filter(i => i.id !== id));
  }

  return (
    <div>
      <h2 className="text-xl mb-4" style={{ color: "var(--color-text)" }}>Team Members</h2>
      <table className="w-full text-sm mb-8" style={{ borderCollapse: "collapse" }}>
        <thead>
          <tr style={{ borderBottom: "2px solid var(--color-border)" }}>
            {["Email", "Name", "Role", ""].map(h => (
              <th key={h} className="text-left py-2 px-3 text-xs uppercase" style={{ color: "var(--color-text-muted)" }}>{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {members.map(m => (
            <tr key={m.user_id} style={{ borderBottom: "1px solid var(--color-border)" }}>
              <td className="py-2 px-3" style={{ color: "var(--color-text)" }}>{m.email}</td>
              <td className="py-2 px-3" style={{ color: "var(--color-text-secondary)" }}>{m.name}</td>
              <td className="py-2 px-3">
                <span className="text-xs px-2 py-0.5" style={{
                  background: m.role === "owner" ? "var(--color-brand)" : "var(--bg-surface)",
                  color: m.role === "owner" ? "var(--color-text-on-brand)" : "var(--color-text)",
                }}>{m.role}</span>
              </td>
              <td className="py-2 px-3 text-right">
                {m.role !== "owner" && (
                  <button onClick={() => removeMember(m.user_id)} className="text-xs cursor-pointer" style={{ color: "var(--color-error, #dc2626)" }}>Remove</button>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      <h2 className="text-xl mb-4" style={{ color: "var(--color-text)" }}>Invite Link</h2>
      <div className="flex gap-3 mb-4">
        <button onClick={createInvite} disabled={loading}
          className="px-4 py-2 text-sm cursor-pointer disabled:opacity-50"
          style={{ background: "var(--color-dark)", color: "var(--color-text-on-brand)" }}
        >{loading ? "Creating..." : "Create Invite Link"}</button>
      </div>
      {inviteLink && (
        <div className="flex gap-2 mb-6">
          <input readOnly value={inviteLink} className="flex-1 px-3 py-2 text-sm"
            style={{ background: "var(--bg-surface)", border: "1px solid var(--color-border)", color: "var(--color-text)" }} />
          <button onClick={() => { navigator.clipboard.writeText(inviteLink); }}
            className="px-3 py-2 text-sm cursor-pointer"
            style={{ background: "var(--bg-surface)", border: "1px solid var(--color-border)", color: "var(--color-text)" }}>Copy</button>
        </div>
      )}

      {invitations.length > 0 && (
        <>
          <h3 className="text-sm mb-2" style={{ color: "var(--color-text-muted)" }}>Active Invitations</h3>
          <table className="w-full text-sm" style={{ borderCollapse: "collapse" }}>
            <thead>
              <tr style={{ borderBottom: "1px solid var(--color-border)" }}>
                {["Token", "Uses", "Expires", ""].map(h => (
                  <th key={h} className="text-left py-1 px-3 text-xs" style={{ color: "var(--color-text-muted)" }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {invitations.map(inv => (
                <tr key={inv.id} style={{ borderBottom: "1px solid var(--color-border)" }}>
                  <td className="py-1 px-3 text-xs font-mono" style={{ color: "var(--color-text)" }}>{inv.token.slice(0, 8)}...</td>
                  <td className="py-1 px-3 text-xs" style={{ color: "var(--color-text-muted)" }}>{inv.use_count}{inv.max_uses != null ? `/${inv.max_uses}` : ""}</td>
                  <td className="py-1 px-3 text-xs" style={{ color: "var(--color-text-muted)" }}>{inv.expires_at ? new Date(inv.expires_at).toLocaleString() : "—"}</td>
                  <td className="py-1 px-3 text-right">
                    <button onClick={() => revokeInvitation(inv.id)} className="text-xs cursor-pointer" style={{ color: "var(--color-error, #dc2626)" }}>Revoke</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      )}
    </div>
  );
}

function AccountTab() {
  const [account, setAccount] = useState<AccountInfo | null>(null);
  const [showDelete, setShowDelete] = useState(false);
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [deleting, setDeleting] = useState(false);

  useEffect(() => {
    fetch("/api/account/").then(r => r.json()).then(setAccount).catch(() => {});
  }, []);

  async function handleExport() {
    window.open("/api/account/export", "_blank");
  }

  async function handleDelete() {
    setDeleting(true);
    setError("");
    try {
      const res = await fetch("/api/account/", {
        method: "DELETE",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ password }),
      });
      if (res.ok) {
        window.location.href = "/login";
      } else {
        const data = await res.json();
        setError(data.detail || "Deletion failed");
      }
    } catch {
      setError("Failed to connect");
    } finally { setDeleting(false); }
  }

  if (!account) return <div className="text-sm" style={{ color: "var(--color-text-muted)" }}>Loading...</div>;

  return (
    <div>
      <h2 className="text-xl mb-4" style={{ color: "var(--color-text)" }}>Account</h2>
      <div className="grid grid-cols-2 gap-4 mb-8 text-sm">
        <div>
          <div className="text-xs" style={{ color: "var(--color-text-muted)" }}>Email</div>
          <div style={{ color: "var(--color-text)" }}>{account.email}</div>
        </div>
        <div>
          <div className="text-xs" style={{ color: "var(--color-text-muted)" }}>Name</div>
          <div style={{ color: "var(--color-text)" }}>{account.name}</div>
        </div>
        <div>
          <div className="text-xs" style={{ color: "var(--color-text-muted)" }}>Member since</div>
          <div style={{ color: "var(--color-text)" }}>{account.created_at ? new Date(account.created_at).toLocaleDateString() : "—"}</div>
        </div>
      </div>

      <h2 className="text-xl mb-4" style={{ color: "var(--color-text)" }}>Export</h2>
      <button onClick={handleExport} className="px-4 py-2 text-sm cursor-pointer mb-8"
        style={{ background: "var(--color-dark)", color: "var(--color-text-on-brand)" }}>
        Export Knowledge Base
      </button>

      <div className="p-6 mt-4" style={{ border: "2px solid var(--color-error, #dc2626)" }}>
        <h2 className="text-xl mb-2" style={{ color: "var(--color-error, #dc2626)" }}>Danger Zone</h2>
        {!account.deletion.eligible ? (
          <p className="text-sm" style={{ color: "var(--color-text-muted)" }}>{account.deletion.reason}</p>
        ) : !showDelete ? (
          <div>
            <p className="text-sm mb-3" style={{ color: "var(--color-text-muted)" }}>
              Permanently delete your account, knowledge base, and all associated data. This cannot be undone.
            </p>
            <button onClick={() => setShowDelete(true)} className="px-4 py-2 text-sm cursor-pointer"
              style={{ background: "var(--color-error, #dc2626)", color: "white" }}>Delete Account</button>
          </div>
        ) : (
          <div>
            <p className="text-sm mb-3" style={{ color: "var(--color-text)" }}>Enter your password to confirm:</p>
            <div className="flex gap-3">
              <input type="password" value={password} onChange={e => setPassword(e.target.value)}
                placeholder="Your password" aria-label="Confirm password for account deletion"
                className="px-3 py-2 text-sm" style={{ background: "var(--bg-surface)", border: "1px solid var(--color-border)", color: "var(--color-text)" }} />
              <button onClick={handleDelete} disabled={!password || deleting}
                className="px-4 py-2 text-sm cursor-pointer disabled:opacity-50"
                style={{ background: "var(--color-error, #dc2626)", color: "white" }}>
                {deleting ? "Deleting..." : "Delete My Account"}
              </button>
              <button onClick={() => { setShowDelete(false); setPassword(""); setError(""); }}
                className="px-4 py-2 text-sm cursor-pointer"
                style={{ background: "var(--bg-surface)", border: "1px solid var(--color-border)", color: "var(--color-text)" }}>Cancel</button>
            </div>
            {error && <p className="text-sm mt-2" style={{ color: "var(--color-error, #dc2626)" }}>{error}</p>}
          </div>
        )}
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Add route and nav link to App.tsx**

Read `openraven-ui/src/App.tsx`. Then:

Add import:
```tsx
import SettingsPage from "./pages/SettingsPage";
```

Add route after the `/audit` route:
```tsx
          <Route path="/settings" element={<SettingsPage />} />
```

Add nav link after the Audit link:
```tsx
        <NavLink to="/settings" className={navLinkClass}>{t('nav.settings')}</NavLink>
```

- [ ] **Step 3: Add i18n key**

In `openraven-ui/public/locales/en/common.json`, add to the `nav` object:
```json
    "settings": "Settings"
```

- [ ] **Step 4: Verify UI builds**

```bash
cd /home/ubuntu/source/OpenRaven/openraven-ui && bun run build 2>&1 | tail -5
```

- [ ] **Step 5: Commit**

```bash
cd /home/ubuntu/source/OpenRaven && git add openraven-ui/src/pages/SettingsPage.tsx openraven-ui/src/App.tsx openraven-ui/public/locales/en/common.json && git commit -m "$(cat <<'EOF'
feat(m7): add Settings page with Team and Account tabs

Team tab: member list, invite link creation, invitation management.
Account tab: info, KB export, danger zone with password-confirmed deletion.

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 8: BFF Proxy Routes

**Files:**
- Modify: `openraven-ui/server/index.ts`

- [ ] **Step 1: Add team + account proxy routes**

In `openraven-ui/server/index.ts`, after the audit proxy blocks (around line 115), add:

```typescript
// Team management proxy
app.all("/api/team/*", async (c) => {
  try { return await proxyToCore(c); }
  catch (e) { return c.json({ error: `Core engine error: ${(e as Error).message}` }, 502); }
});
app.all("/api/team", async (c) => {
  try { return await proxyToCore(c); }
  catch (e) { return c.json({ error: `Core engine error: ${(e as Error).message}` }, 502); }
});
// Account management proxy with binary passthrough for zip export
app.all("/api/account/*", async (c) => {
  try {
    if (c.req.path.endsWith("/export")) {
      const url = `${CORE_API_URL}${c.req.path}${c.req.url.includes("?") ? "?" + c.req.url.split("?")[1] : ""}`;
      const res = await fetch(url, {
        method: c.req.method,
        headers: { Cookie: c.req.header("Cookie") ?? "" },
      });
      return new Response(res.body, {
        status: res.status,
        headers: {
          "content-type": res.headers.get("content-type") || "application/zip",
          "content-disposition": res.headers.get("content-disposition") || "attachment; filename=openraven_export.zip",
        },
      });
    }
    return await proxyToCore(c);
  } catch (e) { return c.json({ error: `Core engine error: ${(e as Error).message}` }, 502); }
});
app.all("/api/account", async (c) => {
  try { return await proxyToCore(c); }
  catch (e) { return c.json({ error: `Core engine error: ${(e as Error).message}` }, 502); }
});
```

- [ ] **Step 2: Verify UI builds**

```bash
cd /home/ubuntu/source/OpenRaven/openraven-ui && bun run build 2>&1 | tail -5
```

- [ ] **Step 3: Commit**

```bash
cd /home/ubuntu/source/OpenRaven && git add openraven-ui/server/index.ts && git commit -m "$(cat <<'EOF'
feat(m7): add BFF proxy for team and account API routes

Forwards /api/team/*, /api/account/* to core API.
Account export uses binary passthrough for zip download.

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 9: Final Integration Test

**Files:** None (verification only)

- [ ] **Step 1: Run all Python tests**

```bash
cd /home/ubuntu/source/OpenRaven/openraven && python3 -m pytest tests/ -v --ignore=tests/benchmark --ignore=tests/fixtures 2>&1 | tail -30
```
Expected: All tests pass (existing + new team + account tests).

- [ ] **Step 2: Run UI build**

```bash
cd /home/ubuntu/source/OpenRaven/openraven-ui && bun run build 2>&1 | tail -5
```
Expected: Build succeeds.

- [ ] **Step 3: Verify package still builds**

```bash
cd /home/ubuntu/source/OpenRaven/openraven && python3 -m build 2>&1 | tail -5
```
Expected: Build succeeds.
