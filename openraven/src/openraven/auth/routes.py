"""Auth API routes: signup, login, logout, me, Google OAuth, password reset."""

import secrets
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Request, Response, HTTPException
from sqlalchemy import insert, select, update
from sqlalchemy.engine import Engine

from openraven.auth.db import users, tenants, tenant_members
from openraven.auth.models import (
    UserCreate, UserLogin, UserResponse, TenantResponse, AuthMeResponse,
    PasswordResetRequest, PasswordResetConfirm, LocaleUpdate,
)
from openraven.auth.passwords import hash_password, verify_password
from openraven.auth.sessions import create_session, validate_session, delete_session

# Simple in-memory rate limiter for auth endpoints
_login_attempts: dict[str, list[float]] = {}
_RATE_LIMIT_WINDOW = 60  # seconds
_RATE_LIMIT_MAX = 10  # attempts per window

SUPPORTED_LOCALES = {"en", "zh-TW", "zh-CN", "ja", "ko", "fr", "es", "nl", "it", "vi", "th", "ru"}


def _check_rate_limit(ip: str) -> None:
    """Raise 429 if IP exceeds login rate limit."""
    now = datetime.now(timezone.utc).timestamp()
    attempts = _login_attempts.get(ip, [])
    # Prune old attempts
    attempts = [t for t in attempts if now - t < _RATE_LIMIT_WINDOW]
    if len(attempts) >= _RATE_LIMIT_MAX:
        raise HTTPException(429, "Too many attempts. Try again later.")
    attempts.append(now)
    _login_attempts[ip] = attempts


def _create_user_with_tenant(
    engine: Engine, user_id: str, email: str, name: str,
    password_hash: str | None = None, google_id: str | None = None,
    avatar_url: str | None = None, email_verified: bool = False,
) -> str:
    """Create a user and their default tenant. Returns tenant_id."""
    now = datetime.now(timezone.utc)
    tenant_id = str(uuid.uuid4())
    with engine.connect() as conn:
        conn.execute(insert(users).values(
            id=user_id, email=email, name=name,
            password_hash=password_hash, google_id=google_id,
            avatar_url=avatar_url, email_verified=email_verified,
            created_at=now, updated_at=now,
        ))
        conn.execute(insert(tenants).values(
            id=tenant_id, name=f"{name}'s workspace",
            owner_user_id=user_id, created_at=now,
        ))
        conn.execute(insert(tenant_members).values(
            tenant_id=tenant_id, user_id=user_id, role="owner",
        ))
        conn.commit()
    return tenant_id


def _set_session_cookie(response: Response, session_id: str, secure: bool = False) -> None:
    """Set session cookie with security flags."""
    response.set_cookie(
        "session_id", session_id,
        httponly=True, samesite="lax", secure=secure,
        max_age=7 * 24 * 3600,
    )


def create_auth_router(
    engine: Engine,
    google_client_id: str = "",
    google_client_secret: str = "",
    secure_cookies: bool = False,
) -> APIRouter:
    router = APIRouter(prefix="/api/auth")

    @router.post("/signup")
    async def signup(data: UserCreate, request: Request, response: Response):
        _check_rate_limit(request.client.host if request.client else "unknown")

        if len(data.password) < 8:
            raise HTTPException(400, "Password must be at least 8 characters")

        with engine.connect() as conn:
            existing = conn.execute(
                select(users.c.id).where(users.c.email == data.email)
            ).first()
            if existing:
                raise HTTPException(409, "Email already registered")

        user_id = str(uuid.uuid4())
        tenant_id = _create_user_with_tenant(
            engine, user_id, data.email, data.name,
            password_hash=hash_password(data.password),
        )

        session_id = create_session(engine, user_id)
        _set_session_cookie(response, session_id, secure=secure_cookies)
        return {
            "user": UserResponse(id=user_id, email=data.email, name=data.name).model_dump(),
            "tenant": TenantResponse(id=tenant_id, name=f"{data.name}'s workspace").model_dump(),
        }

    @router.post("/login")
    async def login(data: UserLogin, request: Request, response: Response):
        _check_rate_limit(request.client.host if request.client else "unknown")

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
        _set_session_cookie(response, session_id, secure=secure_cookies)
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
                select(users.c.id, users.c.email, users.c.name, users.c.avatar_url, users.c.email_verified, users.c.locale)
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
                locale=user_row.locale,
            ),
            tenant=TenantResponse(
                id=tenant_row.id, name=tenant_row.name,
                storage_quota_mb=tenant_row.storage_quota_mb,
            ),
        ).model_dump()

    @router.patch("/locale")
    async def update_locale(data: LocaleUpdate, request: Request):
        session_id = request.cookies.get("session_id")
        if not session_id:
            raise HTTPException(401, "Not authenticated")
        ctx = validate_session(engine, session_id)
        if not ctx:
            raise HTTPException(401, "Session expired")
        if data.locale not in SUPPORTED_LOCALES:
            raise HTTPException(400, f"Unsupported locale: {data.locale}")
        with engine.connect() as conn:
            conn.execute(
                update(users).where(users.c.id == ctx.user_id).values(locale=data.locale)
            )
            conn.commit()
        return {"ok": True}

    # --- Google OAuth ---

    @router.get("/google")
    async def google_auth(request: Request, response: Response):
        if not google_client_id:
            raise HTTPException(501, "Google OAuth not configured")
        from openraven.auth.google_oauth import build_google_auth_url
        redirect_uri = str(request.base_url) + "api/auth/google/callback"
        state = secrets.token_urlsafe(32)
        response.set_cookie("oauth_state", state, httponly=True, samesite="lax", max_age=600)
        url = build_google_auth_url(google_client_id, redirect_uri, state=state)
        from fastapi.responses import RedirectResponse
        resp = RedirectResponse(url)
        resp.set_cookie("oauth_state", state, httponly=True, samesite="lax", max_age=600)
        return resp

    @router.get("/google/callback")
    async def google_callback(request: Request, code: str, state: str = ""):
        if not google_client_id or not google_client_secret:
            raise HTTPException(501, "Google OAuth not configured")

        # Verify CSRF state
        expected_state = request.cookies.get("oauth_state", "")
        if not state or state != expected_state:
            raise HTTPException(400, "Invalid OAuth state — possible CSRF attack")

        from openraven.auth.google_oauth import exchange_google_code
        redirect_uri = str(request.base_url) + "api/auth/google/callback"
        profile = await exchange_google_code(code, google_client_id, google_client_secret, redirect_uri)

        google_id = profile.get("id", "")
        email = profile.get("email", "")
        name = profile.get("name", email)
        avatar_url = profile.get("picture", "")

        with engine.connect() as conn:
            existing = conn.execute(
                select(users.c.id, users.c.google_id)
                .where((users.c.google_id == google_id) | (users.c.email == email))
            ).first()

            if existing:
                user_id = existing.id
                if not existing.google_id:
                    conn.execute(
                        update(users).where(users.c.id == user_id)
                        .values(google_id=google_id, avatar_url=avatar_url)
                    )
                    conn.commit()
            else:
                user_id = str(uuid.uuid4())
                _create_user_with_tenant(
                    engine, user_id, email, name,
                    google_id=google_id, avatar_url=avatar_url,
                    email_verified=True,
                )

        session_id = create_session(engine, user_id)
        from fastapi.responses import RedirectResponse
        resp = RedirectResponse("/")
        _set_session_cookie(resp, session_id, secure=secure_cookies)
        resp.delete_cookie("oauth_state")
        return resp

    # --- Password Reset ---

    @router.post("/reset-password")
    async def request_reset(data: PasswordResetRequest, request: Request):
        _check_rate_limit(request.client.host if request.client else "unknown")
        from openraven.auth.reset import create_reset_token
        token = create_reset_token(engine, data.email)
        result: dict = {"ok": True, "message": "If the email exists, a reset link was sent."}
        if token:
            # In dev/test mode, return token directly (no email service yet)
            result["reset_token"] = token
        return result

    @router.post("/reset-password/{token}")
    async def confirm_reset(token: str, data: PasswordResetConfirm):
        if len(data.password) < 8:
            raise HTTPException(400, "Password must be at least 8 characters")
        from openraven.auth.reset import consume_reset_token
        success = consume_reset_token(engine, token, data.password)
        if not success:
            raise HTTPException(400, "Invalid or expired reset token")
        return {"ok": True}

    return router
