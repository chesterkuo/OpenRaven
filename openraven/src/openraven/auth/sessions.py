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
