"""Team management API routes."""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Request, HTTPException
from sqlalchemy import select, delete
from sqlalchemy.engine import Engine

from openraven.auth.db import tenants, tenant_members, users, invitations
from openraven.auth.invitations import (
    create_invitation, accept_invitation, list_invitations, revoke_invitation,
)


def create_team_router(engine: Engine) -> APIRouter:
    router = APIRouter()

    def _require_owner(request: Request) -> tuple[str, str]:
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
        auth = getattr(request.state, "auth", None)
        if not auth:
            raise HTTPException(401, "Not authenticated")
        return auth.user_id, auth.tenant_id

    @router.post("/invite")
    async def create_invite(request: Request):
        user_id, tenant_id = _require_owner(request)
        return create_invitation(engine, tenant_id, user_id)

    @router.get("/invite/{token}")
    async def validate_invite(token: str):
        with engine.connect() as conn:
            row = conn.execute(select(invitations).where(invitations.c.token == token)).first()
        if not row:
            return {"valid": False, "reason": "not_found"}
        now = datetime.now(timezone.utc)
        expires = row.expires_at
        if hasattr(expires, 'replace') and expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        if expires < now:
            return {"valid": False, "reason": "expired"}
        if row.max_uses is not None and row.use_count >= row.max_uses:
            return {"valid": False, "reason": "maxed"}
        with engine.connect() as conn:
            tenant = conn.execute(select(tenants.c.name).where(tenants.c.id == row.tenant_id)).first()
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
                    tenant_members.c.user_id, tenant_members.c.role,
                    users.c.email, users.c.name, users.c.created_at,
                )
                .join(users, tenant_members.c.user_id == users.c.id)
                .where(tenant_members.c.tenant_id == tenant_id)
            ).fetchall()
        return [
            {"user_id": r.user_id, "email": r.email, "name": r.name, "role": r.role,
             "joined_at": r.created_at.isoformat() if r.created_at else None}
            for r in rows
        ]

    @router.delete("/members/{user_id}")
    async def remove_member(user_id: str, request: Request):
        owner_id, tenant_id = _require_owner(request)
        if user_id == owner_id:
            raise HTTPException(400, "Cannot remove yourself as owner")
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
