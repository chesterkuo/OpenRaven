"""Auth API routes: signup, login, logout, me."""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Request, Response, HTTPException
from sqlalchemy import insert, select
from sqlalchemy.engine import Engine

from openraven.auth.db import users, tenants, tenant_members
from openraven.auth.models import (
    UserCreate, UserLogin, UserResponse, TenantResponse, AuthMeResponse,
    PasswordResetRequest, PasswordResetConfirm,
)
from openraven.auth.passwords import hash_password, verify_password
from openraven.auth.sessions import create_session, validate_session, delete_session


def create_auth_router(engine: Engine, google_client_id: str = "", google_client_secret: str = "") -> APIRouter:
    router = APIRouter(prefix="/api/auth")

    @router.post("/signup")
    async def signup(data: UserCreate, response: Response):
        with engine.connect() as conn:
            existing = conn.execute(
                select(users.c.id).where(users.c.email == data.email)
            ).first()
            if existing:
                raise HTTPException(409, "Email already registered")

            user_id = str(uuid.uuid4())
            now = datetime.now(timezone.utc)
            conn.execute(insert(users).values(
                id=user_id, email=data.email, name=data.name,
                password_hash=hash_password(data.password),
                created_at=now, updated_at=now,
            ))

            tenant_id = str(uuid.uuid4())
            conn.execute(insert(tenants).values(
                id=tenant_id, name=f"{data.name}'s workspace",
                owner_user_id=user_id, created_at=now,
            ))
            conn.execute(insert(tenant_members).values(
                tenant_id=tenant_id, user_id=user_id, role="owner",
            ))
            conn.commit()

        session_id = create_session(engine, user_id)
        response.set_cookie(
            "session_id", session_id,
            httponly=True, samesite="lax", max_age=7 * 24 * 3600,
        )
        return {
            "user": UserResponse(id=user_id, email=data.email, name=data.name).model_dump(),
            "tenant": TenantResponse(id=tenant_id, name=f"{data.name}'s workspace").model_dump(),
        }

    @router.post("/login")
    async def login(data: UserLogin, response: Response):
        with engine.connect() as conn:
            row = conn.execute(
                select(users.c.id, users.c.email, users.c.name, users.c.password_hash)
                .where(users.c.email == data.email)
            ).first()
        if not row or not row.password_hash:
            raise HTTPException(401, "Invalid email or password")
        if not verify_password(data.password, row.password_hash):
            raise HTTPException(401, "Invalid email or password")

        session_id = create_session(engine, row.id)
        response.set_cookie(
            "session_id", session_id,
            httponly=True, samesite="lax", max_age=7 * 24 * 3600,
        )
        return {"user": UserResponse(id=row.id, email=row.email, name=row.name).model_dump()}

    @router.post("/logout")
    async def logout(request: Request, response: Response):
        session_id = request.cookies.get("session_id")
        if session_id:
            delete_session(engine, session_id)
        response.delete_cookie("session_id")
        return {"ok": True}

    @router.get("/me")
    async def me(request: Request):
        session_id = request.cookies.get("session_id")
        if not session_id:
            raise HTTPException(401, "Not authenticated")
        ctx = validate_session(engine, session_id)
        if not ctx:
            raise HTTPException(401, "Session expired")

        with engine.connect() as conn:
            user_row = conn.execute(
                select(users.c.id, users.c.email, users.c.name, users.c.avatar_url, users.c.email_verified)
                .where(users.c.id == ctx.user_id)
            ).first()
            tenant_row = conn.execute(
                select(tenants.c.id, tenants.c.name, tenants.c.storage_quota_mb)
                .where(tenants.c.id == ctx.tenant_id)
            ).first()

        if not user_row or not tenant_row:
            raise HTTPException(401, "User or tenant not found")

        return AuthMeResponse(
            user=UserResponse(
                id=user_row.id, email=user_row.email, name=user_row.name,
                avatar_url=user_row.avatar_url, email_verified=user_row.email_verified or False,
            ),
            tenant=TenantResponse(
                id=tenant_row.id, name=tenant_row.name,
                storage_quota_mb=tenant_row.storage_quota_mb,
            ),
        ).model_dump()

    return router
