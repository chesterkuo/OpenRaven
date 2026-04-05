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

        conn.execute(
            update(users).where(users.c.id == row.user_id)
            .values(password_hash=hash_password(new_password), updated_at=datetime.now(timezone.utc))
        )
        conn.execute(
            update(password_reset_tokens)
            .where(password_reset_tokens.c.id == row.id)
            .values(used=True)
        )
        conn.commit()
    return True
