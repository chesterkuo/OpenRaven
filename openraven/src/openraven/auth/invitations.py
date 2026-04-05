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
    inv_id = str(uuid.uuid4())
    token = secrets.token_hex(16)
    expires_at = datetime.now(timezone.utc) + timedelta(hours=expires_hours)
    with engine.connect() as conn:
        conn.execute(insert(invitations).values(
            id=inv_id, tenant_id=tenant_id, token=token, created_by=created_by,
            expires_at=expires_at, max_uses=max_uses, use_count=0,
        ))
        conn.commit()
    return {"id": inv_id, "token": token, "expires_at": expires_at.isoformat()}


def accept_invitation(engine: Engine, token: str, user_id: str) -> str:
    with engine.connect() as conn:
        row = conn.execute(select(invitations).where(invitations.c.token == token)).first()
        if not row:
            raise ValueError("Invitation not found")
        now = datetime.now(timezone.utc)
        expires = row.expires_at
        if hasattr(expires, 'replace') and expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        if expires < now:
            raise ValueError("Invitation has expired")
        if row.max_uses is not None and row.use_count >= row.max_uses:
            raise ValueError("Invitation has reached its maximum uses")
        existing = conn.execute(
            select(tenant_members).where(
                tenant_members.c.tenant_id == row.tenant_id,
                tenant_members.c.user_id == user_id,
            )
        ).first()
        if existing:
            raise ValueError("User is already a member of this tenant")
        conn.execute(insert(tenant_members).values(
            tenant_id=row.tenant_id, user_id=user_id, role="member",
        ))
        conn.execute(
            update(invitations).where(invitations.c.id == row.id)
            .values(use_count=row.use_count + 1)
        )
        conn.commit()
    return row.tenant_id


def list_invitations(engine: Engine, tenant_id: str) -> list[dict]:
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
            "id": row.id, "token": row.token,
            "expires_at": row.expires_at.isoformat() if row.expires_at else None,
            "max_uses": row.max_uses, "use_count": row.use_count,
            "created_at": row.created_at.isoformat() if row.created_at else None,
        }
        for row in rows
    ]


def revoke_invitation(engine: Engine, invitation_id: str, tenant_id: str) -> bool:
    with engine.connect() as conn:
        result = conn.execute(
            delete(invitations).where(
                invitations.c.id == invitation_id,
                invitations.c.tenant_id == tenant_id,
            )
        )
        conn.commit()
    return result.rowcount > 0
