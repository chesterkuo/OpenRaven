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
            user = conn.execute(select(users).where(users.c.id == auth.user_id)).first()
        if not user:
            raise HTTPException(404, "User not found")
        eligibility = check_deletion_eligibility(engine, auth.user_id)
        return {
            "user_id": user.id, "email": user.email, "name": user.name,
            "created_at": user.created_at.isoformat() if user.created_at else None,
            "deletion": eligibility,
        }

    @router.get("/export")
    async def export_kb(request: Request):
        auth = _get_auth(request)
        data_dir = data_root / auth.tenant_id
        if not data_dir.exists():
            raise HTTPException(404, "No knowledge base data found")
        export_dir = Path(tempfile.mkdtemp())
        zip_path = export_knowledge_base(data_dir, export_dir)
        return FileResponse(path=str(zip_path), media_type="application/zip", filename="openraven_export.zip")

    @router.delete("/")
    async def delete_my_account(request: Request, body: DeleteRequest):
        auth = _get_auth(request)
        with engine.connect() as conn:
            user = conn.execute(select(users.c.password_hash).where(users.c.id == auth.user_id)).first()
        if not user or not user.password_hash:
            raise HTTPException(400, "Cannot verify password (OAuth-only account)")
        if not verify_password(body.password, user.password_hash):
            raise HTTPException(403, "Incorrect password")
        eligibility = check_deletion_eligibility(engine, auth.user_id)
        if not eligibility["eligible"]:
            raise HTTPException(400, eligibility["reason"])
        data_dir = data_root / auth.tenant_id
        delete_account(engine, auth.user_id, eligibility["tenant_id"], data_dir)
        return {"deleted": True}

    return router
