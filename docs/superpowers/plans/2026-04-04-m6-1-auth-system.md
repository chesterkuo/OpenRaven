# M6.1: PostgreSQL + Auth System — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add user authentication (email/password + Google OAuth) backed by PostgreSQL, with session-based auth middleware protecting all API routes.

**Architecture:** Lucia v3 for session management, bcrypt for password hashing, PostgreSQL for user/session/tenant storage. FastAPI dependency injection for auth middleware. Hono BFF forwards session cookies to core API. Existing SQLite MetadataStore remains for file metadata (tenant-scoped in M6.2).

**Tech Stack:** PostgreSQL 16, Lucia v3, bcrypt, asyncpg, SQLAlchemy (Core, not ORM), Alembic, Google OAuth 2.0

**Spec:** `docs/superpowers/specs/2026-04-04-m6-managed-saas-design.md` — Section 1 (Auth System)

---

## File Structure

| File | Action | Responsibility |
|------|--------|---------------|
| `openraven/src/openraven/auth/__init__.py` | Create | Auth package init |
| `openraven/src/openraven/auth/db.py` | Create | PostgreSQL connection pool, table definitions (SQLAlchemy Core) |
| `openraven/src/openraven/auth/models.py` | Create | Pydantic models for User, Session, Tenant |
| `openraven/src/openraven/auth/passwords.py` | Create | bcrypt hash + verify |
| `openraven/src/openraven/auth/sessions.py` | Create | Create/validate/delete sessions, cookie helpers |
| `openraven/src/openraven/auth/google_oauth.py` | Create | Google OAuth signup/login flow (reuses existing google_auth patterns) |
| `openraven/src/openraven/auth/middleware.py` | Create | FastAPI dependency `require_auth()` → returns AuthContext |
| `openraven/src/openraven/auth/routes.py` | Create | Auth API endpoints (/api/auth/*) |
| `openraven/src/openraven/auth/reset.py` | Create | Password reset token generation + validation |
| `openraven/src/openraven/config.py` | Modify | Add DATABASE_URL, SESSION_SECRET, GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET |
| `openraven/src/openraven/api/server.py` | Modify | Mount auth routes, add auth middleware to existing routes |
| `openraven/pyproject.toml` | Modify | Add asyncpg, sqlalchemy, bcrypt, alembic dependencies |
| `openraven/alembic.ini` | Create | Alembic config |
| `openraven/alembic/env.py` | Create | Alembic migration environment |
| `openraven/alembic/versions/001_auth_tables.py` | Create | Initial migration: users, sessions, tenants, tenant_members, password_reset_tokens |
| `openraven/tests/test_auth.py` | Create | Auth unit tests |
| `openraven/tests/test_auth_api.py` | Create | Auth API integration tests |

---

### Task 1: Install Dependencies

**Files:**
- Modify: `openraven/pyproject.toml`

- [ ] **Step 1: Add auth dependencies to pyproject.toml**

In `openraven/pyproject.toml`, add these to the `dependencies` list:

```toml
"asyncpg>=0.29.0",
"sqlalchemy[asyncio]>=2.0.0",
"bcrypt>=4.1.0",
"alembic>=1.13.0",
"python-multipart>=0.0.9",
```

- [ ] **Step 2: Install dependencies**

```bash
cd openraven && pip install -e ".[dev]"
```

Expected: Installation succeeds.

- [ ] **Step 3: Verify imports work**

```bash
python -c "import asyncpg; import sqlalchemy; import bcrypt; import alembic; print('OK')"
```

Expected: `OK`

- [ ] **Step 4: Commit**

```bash
cd openraven && git add pyproject.toml
git commit -m "chore(m6): add PostgreSQL auth dependencies (asyncpg, sqlalchemy, bcrypt, alembic)"
```

---

### Task 2: PostgreSQL Database Layer

**Files:**
- Create: `openraven/src/openraven/auth/__init__.py`
- Create: `openraven/src/openraven/auth/db.py`
- Create: `openraven/src/openraven/auth/models.py`
- Test: `openraven/tests/test_auth.py`

- [ ] **Step 1: Create auth package init**

Create `openraven/src/openraven/auth/__init__.py`:

```python
"""Authentication and authorization for OpenRaven."""
```

- [ ] **Step 2: Write the failing test for DB connection**

Create `openraven/tests/test_auth.py`:

```python
import pytest
from openraven.auth.db import create_tables, get_engine
from openraven.auth.models import UserCreate


def test_create_tables_creates_users_table():
    """Tables should be created without error on a fresh SQLite DB."""
    engine = get_engine("sqlite:///test_auth.db")
    create_tables(engine)
    from sqlalchemy import inspect
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    assert "users" in tables
    assert "sessions" in tables
    assert "tenants" in tables
    assert "tenant_members" in tables
    assert "password_reset_tokens" in tables
    import os
    os.remove("test_auth.db")


def test_user_create_model_validates_email():
    user = UserCreate(name="Test", email="test@example.com", password="securepass123")
    assert user.email == "test@example.com"
    assert user.name == "Test"
```

- [ ] **Step 3: Run test to verify it fails**

```bash
cd openraven && pytest tests/test_auth.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'openraven.auth.db'`

- [ ] **Step 4: Implement db.py with table definitions**

Create `openraven/src/openraven/auth/db.py`:

```python
"""PostgreSQL database connection and table definitions."""

from sqlalchemy import (
    MetaData, Table, Column, String, Boolean, Integer, DateTime, ForeignKey,
    CheckConstraint, UniqueConstraint, create_engine, text,
)
from sqlalchemy.engine import Engine
from datetime import datetime, timezone

metadata = MetaData()

users = Table(
    "users", metadata,
    Column("id", String(36), primary_key=True),
    Column("email", String(255), unique=True, nullable=False),
    Column("name", String(255), nullable=False),
    Column("avatar_url", String(1024)),
    Column("google_id", String(255), unique=True),
    Column("password_hash", String(255)),
    Column("email_verified", Boolean, default=False),
    Column("created_at", DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)),
    Column("updated_at", DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)),
    CheckConstraint(
        "google_id IS NOT NULL OR password_hash IS NOT NULL",
        name="auth_method_check",
    ),
)

sessions = Table(
    "sessions", metadata,
    Column("id", String(255), primary_key=True),
    Column("user_id", String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
    Column("expires_at", DateTime(timezone=True), nullable=False),
    Column("created_at", DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)),
)

tenants = Table(
    "tenants", metadata,
    Column("id", String(36), primary_key=True),
    Column("name", String(255), nullable=False),
    Column("owner_user_id", String(36), ForeignKey("users.id"), nullable=False),
    Column("storage_quota_mb", Integer, default=500),
    Column("created_at", DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)),
)

tenant_members = Table(
    "tenant_members", metadata,
    Column("tenant_id", String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
    Column("user_id", String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
    Column("role", String(20), nullable=False, default="owner"),
    UniqueConstraint("tenant_id", "user_id", name="uq_tenant_user"),
)

password_reset_tokens = Table(
    "password_reset_tokens", metadata,
    Column("id", String(36), primary_key=True),
    Column("user_id", String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
    Column("token_hash", String(255), nullable=False),
    Column("expires_at", DateTime(timezone=True), nullable=False),
    Column("used", Boolean, default=False),
)


def get_engine(database_url: str) -> Engine:
    """Create a SQLAlchemy engine from a database URL."""
    return create_engine(database_url, echo=False)


def create_tables(engine: Engine) -> None:
    """Create all auth tables if they don't exist."""
    metadata.create_all(engine)
```

- [ ] **Step 5: Implement models.py with Pydantic models**

Create `openraven/src/openraven/auth/models.py`:

```python
"""Pydantic models for auth data."""

from pydantic import BaseModel, EmailStr
from datetime import datetime


class UserCreate(BaseModel):
    name: str
    email: str
    password: str


class UserLogin(BaseModel):
    email: str
    password: str


class UserResponse(BaseModel):
    id: str
    email: str
    name: str
    avatar_url: str | None = None
    email_verified: bool = False


class TenantResponse(BaseModel):
    id: str
    name: str
    storage_quota_mb: int = 500


class AuthContext(BaseModel):
    user_id: str
    tenant_id: str
    email: str


class AuthMeResponse(BaseModel):
    user: UserResponse
    tenant: TenantResponse


class PasswordResetRequest(BaseModel):
    email: str


class PasswordResetConfirm(BaseModel):
    password: str
```

- [ ] **Step 6: Run tests**

```bash
cd openraven && pytest tests/test_auth.py -v
```

Expected: 2 tests PASS.

- [ ] **Step 7: Commit**

```bash
cd openraven && git add src/openraven/auth/ tests/test_auth.py
git commit -m "feat(m6): add auth DB schema and Pydantic models"
```

---

### Task 3: Password Hashing

**Files:**
- Create: `openraven/src/openraven/auth/passwords.py`
- Test: `openraven/tests/test_auth.py` (append)

- [ ] **Step 1: Write failing tests**

Append to `openraven/tests/test_auth.py`:

```python
from openraven.auth.passwords import hash_password, verify_password


def test_hash_password_returns_bcrypt_hash():
    hashed = hash_password("mysecret123")
    assert hashed.startswith("$2b$")
    assert len(hashed) == 60


def test_verify_password_correct():
    hashed = hash_password("mysecret123")
    assert verify_password("mysecret123", hashed) is True


def test_verify_password_incorrect():
    hashed = hash_password("mysecret123")
    assert verify_password("wrongpassword", hashed) is False
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd openraven && pytest tests/test_auth.py::test_hash_password_returns_bcrypt_hash -v
```

Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Implement passwords.py**

Create `openraven/src/openraven/auth/passwords.py`:

```python
"""Password hashing with bcrypt."""

import bcrypt


def hash_password(password: str) -> str:
    """Hash a password with bcrypt."""
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, hashed: str) -> bool:
    """Verify a password against a bcrypt hash."""
    return bcrypt.checkpw(password.encode(), hashed.encode())
```

- [ ] **Step 4: Run tests**

```bash
cd openraven && pytest tests/test_auth.py -v -k "password"
```

Expected: 3 tests PASS.

- [ ] **Step 5: Commit**

```bash
cd openraven && git add src/openraven/auth/passwords.py tests/test_auth.py
git commit -m "feat(m6): add bcrypt password hashing"
```

---

### Task 4: Session Management

**Files:**
- Create: `openraven/src/openraven/auth/sessions.py`
- Test: `openraven/tests/test_auth.py` (append)

- [ ] **Step 1: Write failing tests**

Append to `openraven/tests/test_auth.py`:

```python
import os
from openraven.auth.sessions import create_session, validate_session, delete_session
from openraven.auth.db import get_engine, create_tables, users, tenants, tenant_members, sessions
from sqlalchemy import insert
from datetime import datetime, timezone, timedelta
import uuid


@pytest.fixture
def db_engine():
    engine = get_engine("sqlite:///test_sessions.db")
    create_tables(engine)
    yield engine
    import os
    os.remove("test_sessions.db")


@pytest.fixture
def test_user(db_engine):
    user_id = str(uuid.uuid4())
    tenant_id = str(uuid.uuid4())
    with db_engine.connect() as conn:
        conn.execute(insert(users).values(
            id=user_id, email="test@example.com", name="Test User",
            password_hash="$2b$12$fakehashfakehashfakehashfakehashfakehashfakehashfake",
            created_at=datetime.now(timezone.utc), updated_at=datetime.now(timezone.utc),
        ))
        conn.execute(insert(tenants).values(
            id=tenant_id, name="Test Workspace", owner_user_id=user_id,
            created_at=datetime.now(timezone.utc),
        ))
        conn.execute(insert(tenant_members).values(
            tenant_id=tenant_id, user_id=user_id, role="owner",
        ))
        conn.commit()
    return {"user_id": user_id, "tenant_id": tenant_id}


def test_create_session_returns_session_id(db_engine, test_user):
    session_id = create_session(db_engine, test_user["user_id"])
    assert isinstance(session_id, str)
    assert len(session_id) > 20


def test_validate_session_returns_auth_context(db_engine, test_user):
    session_id = create_session(db_engine, test_user["user_id"])
    ctx = validate_session(db_engine, session_id)
    assert ctx is not None
    assert ctx.user_id == test_user["user_id"]
    assert ctx.tenant_id == test_user["tenant_id"]
    assert ctx.email == "test@example.com"


def test_validate_session_expired_returns_none(db_engine, test_user):
    session_id = create_session(db_engine, test_user["user_id"], ttl_hours=-1)
    ctx = validate_session(db_engine, session_id)
    assert ctx is None


def test_delete_session(db_engine, test_user):
    session_id = create_session(db_engine, test_user["user_id"])
    delete_session(db_engine, session_id)
    ctx = validate_session(db_engine, session_id)
    assert ctx is None
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd openraven && pytest tests/test_auth.py::test_create_session_returns_session_id -v
```

Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Implement sessions.py**

Create `openraven/src/openraven/auth/sessions.py`:

```python
"""Session creation, validation, and deletion."""

import secrets
from datetime import datetime, timezone, timedelta
from sqlalchemy import insert, select, delete
from sqlalchemy.engine import Engine

from openraven.auth.db import sessions, users, tenants, tenant_members
from openraven.auth.models import AuthContext


def create_session(engine: Engine, user_id: str, ttl_hours: int = 24 * 7) -> str:
    """Create a new session for a user. Returns session ID."""
    session_id = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(hours=ttl_hours)
    with engine.connect() as conn:
        conn.execute(insert(sessions).values(
            id=session_id,
            user_id=user_id,
            expires_at=expires_at,
            created_at=datetime.now(timezone.utc),
        ))
        conn.commit()
    return session_id


def validate_session(engine: Engine, session_id: str) -> AuthContext | None:
    """Validate a session ID. Returns AuthContext if valid, None if expired/missing."""
    with engine.connect() as conn:
        row = conn.execute(
            select(sessions.c.user_id, sessions.c.expires_at)
            .where(sessions.c.id == session_id)
        ).first()
        if not row:
            return None
        if row.expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
            conn.execute(delete(sessions).where(sessions.c.id == session_id))
            conn.commit()
            return None
        # Get user email
        user_row = conn.execute(
            select(users.c.email).where(users.c.id == row.user_id)
        ).first()
        if not user_row:
            return None
        # Get tenant
        tenant_row = conn.execute(
            select(tenant_members.c.tenant_id)
            .where(tenant_members.c.user_id == row.user_id)
        ).first()
        if not tenant_row:
            return None
        return AuthContext(
            user_id=row.user_id,
            tenant_id=tenant_row.tenant_id,
            email=user_row.email,
        )


def delete_session(engine: Engine, session_id: str) -> None:
    """Delete a session."""
    with engine.connect() as conn:
        conn.execute(delete(sessions).where(sessions.c.id == session_id))
        conn.commit()
```

- [ ] **Step 4: Run tests**

```bash
cd openraven && pytest tests/test_auth.py -v -k "session"
```

Expected: 4 tests PASS.

- [ ] **Step 5: Commit**

```bash
cd openraven && git add src/openraven/auth/sessions.py tests/test_auth.py
git commit -m "feat(m6): add session management (create, validate, delete)"
```

---

### Task 5: Auth Routes (Signup, Login, Logout, Me)

**Files:**
- Create: `openraven/src/openraven/auth/routes.py`
- Test: `openraven/tests/test_auth_api.py`

- [ ] **Step 1: Write failing API tests**

Create `openraven/tests/test_auth_api.py`:

```python
import pytest
from fastapi.testclient import TestClient
from openraven.auth.db import get_engine, create_tables
from openraven.auth.routes import create_auth_router


@pytest.fixture
def client():
    engine = get_engine("sqlite:///test_auth_api.db")
    create_tables(engine)
    from fastapi import FastAPI
    app = FastAPI()
    app.include_router(create_auth_router(engine))
    yield TestClient(app)
    import os
    os.remove("test_auth_api.db")


def test_signup_creates_user(client):
    res = client.post("/api/auth/signup", json={
        "name": "Alice", "email": "alice@example.com", "password": "securepass123"
    })
    assert res.status_code == 200
    data = res.json()
    assert data["user"]["email"] == "alice@example.com"
    assert data["user"]["name"] == "Alice"
    assert "session_id" not in data  # session is in cookie, not body


def test_signup_sets_session_cookie(client):
    res = client.post("/api/auth/signup", json={
        "name": "Bob", "email": "bob@example.com", "password": "securepass123"
    })
    assert "session_id" in res.cookies


def test_signup_duplicate_email_fails(client):
    client.post("/api/auth/signup", json={
        "name": "Alice", "email": "alice@example.com", "password": "securepass123"
    })
    res = client.post("/api/auth/signup", json={
        "name": "Alice2", "email": "alice@example.com", "password": "otherpass123"
    })
    assert res.status_code == 409


def test_login_valid_credentials(client):
    client.post("/api/auth/signup", json={
        "name": "Alice", "email": "alice@example.com", "password": "securepass123"
    })
    res = client.post("/api/auth/login", json={
        "email": "alice@example.com", "password": "securepass123"
    })
    assert res.status_code == 200
    assert "session_id" in res.cookies


def test_login_wrong_password(client):
    client.post("/api/auth/signup", json={
        "name": "Alice", "email": "alice@example.com", "password": "securepass123"
    })
    res = client.post("/api/auth/login", json={
        "email": "alice@example.com", "password": "wrongpass"
    })
    assert res.status_code == 401


def test_login_nonexistent_email(client):
    res = client.post("/api/auth/login", json={
        "email": "nobody@example.com", "password": "pass"
    })
    assert res.status_code == 401


def test_me_with_session(client):
    client.post("/api/auth/signup", json={
        "name": "Alice", "email": "alice@example.com", "password": "securepass123"
    })
    res = client.get("/api/auth/me")
    assert res.status_code == 200
    data = res.json()
    assert data["user"]["email"] == "alice@example.com"
    assert data["tenant"]["name"] == "Alice's workspace"


def test_me_without_session(client):
    res = client.get("/api/auth/me")
    assert res.status_code == 401


def test_logout_clears_session(client):
    client.post("/api/auth/signup", json={
        "name": "Alice", "email": "alice@example.com", "password": "securepass123"
    })
    res = client.post("/api/auth/logout")
    assert res.status_code == 200
    res = client.get("/api/auth/me")
    assert res.status_code == 401
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd openraven && pytest tests/test_auth_api.py -v
```

Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Implement auth routes**

Create `openraven/src/openraven/auth/routes.py`:

```python
"""Auth API routes: signup, login, logout, me."""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Request, Response, HTTPException
from sqlalchemy import insert, select
from sqlalchemy.engine import Engine

from openraven.auth.db import users, tenants, tenant_members
from openraven.auth.models import UserCreate, UserLogin, UserResponse, TenantResponse, AuthMeResponse
from openraven.auth.passwords import hash_password, verify_password
from openraven.auth.sessions import create_session, validate_session, delete_session


def create_auth_router(engine: Engine) -> APIRouter:
    router = APIRouter(prefix="/api/auth")

    @router.post("/signup")
    async def signup(data: UserCreate, response: Response):
        # Check duplicate email
        with engine.connect() as conn:
            existing = conn.execute(
                select(users.c.id).where(users.c.email == data.email)
            ).first()
            if existing:
                raise HTTPException(409, "Email already registered")

            # Create user
            user_id = str(uuid.uuid4())
            now = datetime.now(timezone.utc)
            conn.execute(insert(users).values(
                id=user_id, email=data.email, name=data.name,
                password_hash=hash_password(data.password),
                created_at=now, updated_at=now,
            ))

            # Create tenant
            tenant_id = str(uuid.uuid4())
            conn.execute(insert(tenants).values(
                id=tenant_id, name=f"{data.name}'s workspace",
                owner_user_id=user_id, created_at=now,
            ))
            conn.execute(insert(tenant_members).values(
                tenant_id=tenant_id, user_id=user_id, role="owner",
            ))
            conn.commit()

        # Create session
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
```

- [ ] **Step 4: Run tests**

```bash
cd openraven && pytest tests/test_auth_api.py -v
```

Expected: 9 tests PASS.

- [ ] **Step 5: Commit**

```bash
cd openraven && git add src/openraven/auth/routes.py tests/test_auth_api.py
git commit -m "feat(m6): add auth API routes (signup, login, logout, me)"
```

---

### Task 6: Auth Middleware for Existing Routes

**Files:**
- Create: `openraven/src/openraven/auth/middleware.py`
- Modify: `openraven/src/openraven/api/server.py`

- [ ] **Step 1: Implement auth middleware as FastAPI dependency**

Create `openraven/src/openraven/auth/middleware.py`:

```python
"""FastAPI dependency for auth-protected routes."""

from fastapi import Request, HTTPException, Depends
from sqlalchemy.engine import Engine

from openraven.auth.sessions import validate_session
from openraven.auth.models import AuthContext


def create_require_auth(engine: Engine):
    """Create a FastAPI dependency that requires authentication."""
    async def require_auth(request: Request) -> AuthContext:
        session_id = request.cookies.get("session_id")
        if not session_id:
            raise HTTPException(401, "Not authenticated")
        ctx = validate_session(engine, session_id)
        if not ctx:
            raise HTTPException(401, "Session expired")
        return ctx
    return require_auth
```

- [ ] **Step 2: Update config.py with database settings**

In `openraven/src/openraven/config.py`, add these fields to the `RavenConfig` dataclass:

```python
database_url: str = field(default_factory=lambda: _env("DATABASE_URL", ""))
session_secret: str = field(default_factory=lambda: _env("SESSION_SECRET", "dev-secret-change-me"))
google_client_id: str = field(default_factory=lambda: _env("GOOGLE_CLIENT_ID", ""))
google_client_secret: str = field(default_factory=lambda: _env("GOOGLE_CLIENT_SECRET", ""))
```

Also add a property:

```python
@property
def auth_enabled(self) -> bool:
    """Auth is enabled when DATABASE_URL is set."""
    return bool(self.database_url)
```

- [ ] **Step 3: Mount auth routes in server.py**

In `openraven/src/openraven/api/server.py`, in the `create_app()` function, after the CORS middleware setup, add:

```python
# Auth setup (only when DATABASE_URL is configured)
auth_engine = None
if config.auth_enabled:
    from openraven.auth.db import get_engine, create_tables
    from openraven.auth.routes import create_auth_router
    from openraven.auth.middleware import create_require_auth
    auth_engine = get_engine(config.database_url)
    create_tables(auth_engine)
    app.include_router(create_auth_router(auth_engine))
```

This is opt-in: when `DATABASE_URL` is not set, auth is disabled and the app works exactly as before (backward compatible).

- [ ] **Step 4: Verify existing tests still pass**

```bash
cd openraven && pytest tests/ -v --ignore=tests/benchmark
```

Expected: All existing tests pass (auth is opt-in, no breaking changes).

- [ ] **Step 5: Commit**

```bash
cd openraven && git add src/openraven/auth/middleware.py src/openraven/config.py src/openraven/api/server.py
git commit -m "feat(m6): integrate auth middleware into FastAPI server (opt-in via DATABASE_URL)"
```

---

### Task 7: Google OAuth Login Route

**Files:**
- Create: `openraven/src/openraven/auth/google_oauth.py`
- Modify: `openraven/src/openraven/auth/routes.py`
- Test: `openraven/tests/test_auth_api.py` (append)

- [ ] **Step 1: Write failing test for Google OAuth URL**

Append to `openraven/tests/test_auth_api.py`:

```python
def test_google_auth_redirect(client):
    """Google auth endpoint should return 501 when GOOGLE_CLIENT_ID is not set."""
    res = client.get("/api/auth/google")
    assert res.status_code == 501
```

- [ ] **Step 2: Implement Google OAuth helper**

Create `openraven/src/openraven/auth/google_oauth.py`:

```python
"""Google OAuth 2.0 flow for user authentication."""

import httpx
from urllib.parse import urlencode


GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"

SCOPES = ["openid", "email", "profile"]


def build_google_auth_url(client_id: str, redirect_uri: str, state: str = "") -> str:
    """Build the Google OAuth consent URL."""
    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": " ".join(SCOPES),
        "access_type": "offline",
        "prompt": "consent",
    }
    if state:
        params["state"] = state
    return f"{GOOGLE_AUTH_URL}?{urlencode(params)}"


async def exchange_google_code(
    code: str, client_id: str, client_secret: str, redirect_uri: str
) -> dict:
    """Exchange authorization code for tokens and user info."""
    async with httpx.AsyncClient() as http:
        token_res = await http.post(GOOGLE_TOKEN_URL, data={
            "code": code,
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code",
        })
        token_res.raise_for_status()
        tokens = token_res.json()

        userinfo_res = await http.get(GOOGLE_USERINFO_URL, headers={
            "Authorization": f"Bearer {tokens['access_token']}"
        })
        userinfo_res.raise_for_status()
        return userinfo_res.json()
```

- [ ] **Step 3: Add Google OAuth routes to routes.py**

Add these routes to the `create_auth_router` function in `openraven/src/openraven/auth/routes.py`. The function needs to accept `google_client_id` and `google_client_secret` parameters:

Update the function signature:
```python
def create_auth_router(engine: Engine, google_client_id: str = "", google_client_secret: str = "") -> APIRouter:
```

Add these routes inside the function:

```python
    @router.get("/google")
    async def google_auth(request: Request):
        if not google_client_id:
            raise HTTPException(501, "Google OAuth not configured")
        from openraven.auth.google_oauth import build_google_auth_url
        redirect_uri = str(request.base_url) + "api/auth/google/callback"
        url = build_google_auth_url(google_client_id, redirect_uri)
        from fastapi.responses import RedirectResponse
        return RedirectResponse(url)

    @router.get("/google/callback")
    async def google_callback(request: Request, response: Response, code: str):
        if not google_client_id or not google_client_secret:
            raise HTTPException(501, "Google OAuth not configured")
        from openraven.auth.google_oauth import exchange_google_code
        redirect_uri = str(request.base_url) + "api/auth/google/callback"
        profile = await exchange_google_code(code, google_client_id, google_client_secret, redirect_uri)

        google_id = profile.get("id", "")
        email = profile.get("email", "")
        name = profile.get("name", email)
        avatar_url = profile.get("picture", "")

        with engine.connect() as conn:
            # Check if user exists by google_id or email
            existing = conn.execute(
                select(users.c.id, users.c.google_id)
                .where((users.c.google_id == google_id) | (users.c.email == email))
            ).first()

            if existing:
                user_id = existing.id
                # Link Google account if not already linked
                if not existing.google_id:
                    from sqlalchemy import update
                    conn.execute(
                        update(users).where(users.c.id == user_id)
                        .values(google_id=google_id, avatar_url=avatar_url)
                    )
                    conn.commit()
            else:
                # Create new user + tenant
                user_id = str(uuid.uuid4())
                tenant_id = str(uuid.uuid4())
                now = datetime.now(timezone.utc)
                conn.execute(insert(users).values(
                    id=user_id, email=email, name=name,
                    google_id=google_id, avatar_url=avatar_url,
                    email_verified=True, created_at=now, updated_at=now,
                ))
                conn.execute(insert(tenants).values(
                    id=tenant_id, name=f"{name}'s workspace",
                    owner_user_id=user_id, created_at=now,
                ))
                conn.execute(insert(tenant_members).values(
                    tenant_id=tenant_id, user_id=user_id, role="owner",
                ))
                conn.commit()

        session_id = create_session(engine, user_id)
        from fastapi.responses import RedirectResponse
        resp = RedirectResponse("/")
        resp.set_cookie(
            "session_id", session_id,
            httponly=True, samesite="lax", max_age=7 * 24 * 3600,
        )
        return resp
```

- [ ] **Step 4: Update server.py to pass Google credentials**

Update the `create_auth_router` call in `server.py`:

```python
app.include_router(create_auth_router(
    auth_engine,
    google_client_id=config.google_client_id,
    google_client_secret=config.google_client_secret,
))
```

- [ ] **Step 5: Run all tests**

```bash
cd openraven && pytest tests/test_auth.py tests/test_auth_api.py -v
```

Expected: All tests PASS (including new Google auth test).

- [ ] **Step 6: Commit**

```bash
cd openraven && git add src/openraven/auth/google_oauth.py src/openraven/auth/routes.py src/openraven/api/server.py tests/test_auth_api.py
git commit -m "feat(m6): add Google OAuth login flow"
```

---

### Task 8: Password Reset

**Files:**
- Create: `openraven/src/openraven/auth/reset.py`
- Modify: `openraven/src/openraven/auth/routes.py`
- Test: `openraven/tests/test_auth_api.py` (append)

- [ ] **Step 1: Write failing tests**

Append to `openraven/tests/test_auth_api.py`:

```python
def test_reset_password_request_nonexistent_email_still_200(client):
    """Should return 200 even for non-existent emails (no email enumeration)."""
    res = client.post("/api/auth/reset-password", json={"email": "nobody@example.com"})
    assert res.status_code == 200


def test_reset_password_request_existing_email(client):
    client.post("/api/auth/signup", json={
        "name": "Alice", "email": "alice@example.com", "password": "securepass123"
    })
    res = client.post("/api/auth/reset-password", json={"email": "alice@example.com"})
    assert res.status_code == 200
    data = res.json()
    # In test mode, the token is returned in response (not emailed)
    assert "reset_token" in data
```

- [ ] **Step 2: Implement reset.py**

Create `openraven/src/openraven/auth/reset.py`:

```python
"""Password reset token management."""

import secrets
import hashlib
import uuid
from datetime import datetime, timezone, timedelta
from sqlalchemy import insert, select, update
from sqlalchemy.engine import Engine

from openraven.auth.db import password_reset_tokens, users
from openraven.auth.passwords import hash_password


def create_reset_token(engine: Engine, email: str) -> str | None:
    """Create a password reset token. Returns raw token or None if email not found."""
    with engine.connect() as conn:
        user_row = conn.execute(
            select(users.c.id).where(users.c.email == email)
        ).first()
        if not user_row:
            return None

        raw_token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
        conn.execute(insert(password_reset_tokens).values(
            id=str(uuid.uuid4()),
            user_id=user_row.id,
            token_hash=token_hash,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        ))
        conn.commit()
    return raw_token


def verify_reset_token(engine: Engine, raw_token: str) -> str | None:
    """Verify a reset token. Returns user_id if valid, None otherwise."""
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    with engine.connect() as conn:
        row = conn.execute(
            select(password_reset_tokens.c.user_id, password_reset_tokens.c.expires_at, password_reset_tokens.c.used)
            .where(password_reset_tokens.c.token_hash == token_hash)
        ).first()
        if not row or row.used:
            return None
        if row.expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
            return None
        return row.user_id


def consume_reset_token(engine: Engine, raw_token: str, new_password: str) -> bool:
    """Use a reset token to set a new password. Returns True if successful."""
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    with engine.connect() as conn:
        row = conn.execute(
            select(password_reset_tokens.c.id, password_reset_tokens.c.user_id,
                   password_reset_tokens.c.expires_at, password_reset_tokens.c.used)
            .where(password_reset_tokens.c.token_hash == token_hash)
        ).first()
        if not row or row.used:
            return False
        if row.expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
            return False

        # Update password
        conn.execute(
            update(users).where(users.c.id == row.user_id)
            .values(password_hash=hash_password(new_password), updated_at=datetime.now(timezone.utc))
        )
        # Mark token as used
        conn.execute(
            update(password_reset_tokens)
            .where(password_reset_tokens.c.id == row.id)
            .values(used=True)
        )
        conn.commit()
    return True
```

- [ ] **Step 3: Add reset routes to routes.py**

Add these routes inside `create_auth_router` in `openraven/src/openraven/auth/routes.py`:

```python
    @router.post("/reset-password")
    async def request_reset(data: PasswordResetRequest):
        from openraven.auth.reset import create_reset_token
        token = create_reset_token(engine, data.email)
        # In production, send email with token. For now, return it (dev mode).
        result = {"ok": True, "message": "If the email exists, a reset link was sent."}
        if token:
            result["reset_token"] = token  # Only in dev/test — remove in production
        return result

    @router.post("/reset-password/{token}")
    async def confirm_reset(token: str, data: PasswordResetConfirm):
        from openraven.auth.reset import consume_reset_token
        success = consume_reset_token(engine, token, data.password)
        if not success:
            raise HTTPException(400, "Invalid or expired reset token")
        return {"ok": True}
```

Add `PasswordResetRequest, PasswordResetConfirm` to the imports from `openraven.auth.models` at the top of routes.py.

- [ ] **Step 4: Run all tests**

```bash
cd openraven && pytest tests/test_auth.py tests/test_auth_api.py -v
```

Expected: All tests PASS.

- [ ] **Step 5: Commit**

```bash
cd openraven && git add src/openraven/auth/reset.py src/openraven/auth/routes.py tests/test_auth_api.py
git commit -m "feat(m6): add password reset flow"
```

---

### Task 9: Alembic Migrations Setup

**Files:**
- Create: `openraven/alembic.ini`
- Create: `openraven/alembic/env.py`
- Create: `openraven/alembic/script.py.mako`
- Create: `openraven/alembic/versions/001_auth_tables.py`

- [ ] **Step 1: Initialize Alembic**

```bash
cd openraven && alembic init alembic
```

- [ ] **Step 2: Update alembic.ini**

In `openraven/alembic.ini`, set:

```ini
sqlalchemy.url = postgresql://openraven:openraven@localhost:5432/openraven
```

- [ ] **Step 3: Update alembic/env.py to use auth metadata**

Replace the `target_metadata` line in `openraven/alembic/env.py`:

```python
from openraven.auth.db import metadata
target_metadata = metadata
```

- [ ] **Step 4: Create initial migration**

Create `openraven/alembic/versions/001_auth_tables.py`:

```python
"""Initial auth tables.

Revision ID: 001
Create Date: 2026-04-04
"""
from alembic import op
import sqlalchemy as sa

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("email", sa.String(255), unique=True, nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("avatar_url", sa.String(1024)),
        sa.Column("google_id", sa.String(255), unique=True),
        sa.Column("password_hash", sa.String(255)),
        sa.Column("email_verified", sa.Boolean, default=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.CheckConstraint("google_id IS NOT NULL OR password_hash IS NOT NULL", name="auth_method_check"),
    )
    op.create_table(
        "sessions",
        sa.Column("id", sa.String(255), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_table(
        "tenants",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("owner_user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("storage_quota_mb", sa.Integer, default=500),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_table(
        "tenant_members",
        sa.Column("tenant_id", sa.String(36), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role", sa.String(20), nullable=False, server_default="owner"),
        sa.UniqueConstraint("tenant_id", "user_id", name="uq_tenant_user"),
    )
    op.create_table(
        "password_reset_tokens",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("token_hash", sa.String(255), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used", sa.Boolean, default=False),
    )


def downgrade() -> None:
    op.drop_table("password_reset_tokens")
    op.drop_table("tenant_members")
    op.drop_table("tenants")
    op.drop_table("sessions")
    op.drop_table("users")
```

- [ ] **Step 5: Verify migration runs (requires PostgreSQL running)**

```bash
cd openraven && alembic upgrade head
```

Expected: Migration applies successfully. (If PostgreSQL isn't running yet, this can be verified after Docker setup in M6.5.)

- [ ] **Step 6: Commit**

```bash
cd openraven && git add alembic.ini alembic/
git commit -m "feat(m6): add Alembic migrations for auth tables"
```

---

### Task 10: Verify Full Auth Flow End-to-End

**Files:**
- All auth files

- [ ] **Step 1: Run all auth tests**

```bash
cd openraven && pytest tests/test_auth.py tests/test_auth_api.py -v
```

Expected: All tests pass (should be ~16 tests total).

- [ ] **Step 2: Run all existing tests to verify no regressions**

```bash
cd openraven && pytest tests/ -v --ignore=tests/benchmark
```

Expected: All existing tests pass. Auth is opt-in (requires `DATABASE_URL`), so no breaking changes.

- [ ] **Step 3: Verify build**

```bash
cd openraven && pip install -e ".[dev]" && python -c "from openraven.auth.routes import create_auth_router; print('OK')"
```

Expected: `OK`

- [ ] **Step 4: Commit any fixes**

```bash
cd openraven && git add -A && git commit -m "fix(m6): auth integration fixes"
```

(Only if fixes were needed.)
