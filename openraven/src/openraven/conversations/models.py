"""Conversation and message persistence."""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone

from sqlalchemy import Engine, select, delete, desc

from openraven.auth.db import conversations, messages


def create_conversation(
    engine: Engine,
    tenant_id: str,
    user_id: str | None,
    title: str | None = None,
    session_id: str | None = None,
    demo_theme: str | None = None,
) -> str:
    """Create a new conversation. Returns conversation ID."""
    convo_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    with engine.connect() as conn:
        conn.execute(conversations.insert().values(
            id=convo_id,
            tenant_id=tenant_id,
            user_id=user_id,
            session_id=session_id,
            title=title,
            demo_theme=demo_theme,
            created_at=now,
            updated_at=now,
        ))
        conn.commit()
    return convo_id


def list_conversations(
    engine: Engine,
    tenant_id: str,
    user_id: str | None = None,
    session_id: str | None = None,
) -> list[dict]:
    """List conversations for a tenant+user, most recent first."""
    query = (
        select(conversations)
        .where(conversations.c.tenant_id == tenant_id)
        .order_by(desc(conversations.c.updated_at))
    )
    if user_id:
        query = query.where(conversations.c.user_id == user_id)
    if session_id:
        query = query.where(conversations.c.session_id == session_id)
    with engine.connect() as conn:
        rows = conn.execute(query).fetchall()
    return [
        {
            "id": r.id,
            "title": r.title,
            "demo_theme": r.demo_theme,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "updated_at": r.updated_at.isoformat() if r.updated_at else None,
        }
        for r in rows
    ]


def get_conversation(
    engine: Engine,
    convo_id: str,
    tenant_id: str,
    user_id: str | None = None,
    session_id: str | None = None,
) -> dict | None:
    """Get a conversation by ID, scoped to tenant + user/session."""
    query = (
        select(conversations)
        .where(conversations.c.id == convo_id)
        .where(conversations.c.tenant_id == tenant_id)
    )
    if user_id:
        query = query.where(conversations.c.user_id == user_id)
    if session_id:
        query = query.where(conversations.c.session_id == session_id)
    with engine.connect() as conn:
        row = conn.execute(query).fetchone()
    if not row:
        return None
    return {
        "id": row.id,
        "tenant_id": row.tenant_id,
        "user_id": row.user_id,
        "session_id": row.session_id,
        "title": row.title,
        "demo_theme": row.demo_theme,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


def delete_conversation(
    engine: Engine,
    convo_id: str,
    tenant_id: str,
    user_id: str | None = None,
    session_id: str | None = None,
) -> None:
    """Delete a conversation and its messages (cascade), scoped to tenant + user/session."""
    query = (
        delete(conversations)
        .where(conversations.c.id == convo_id)
        .where(conversations.c.tenant_id == tenant_id)
    )
    if user_id:
        query = query.where(conversations.c.user_id == user_id)
    if session_id:
        query = query.where(conversations.c.session_id == session_id)
    with engine.connect() as conn:
        conn.execute(query)
        conn.commit()


def add_message(
    engine: Engine,
    conversation_id: str,
    role: str,
    content: str,
    sources: list[dict] | None = None,
) -> str:
    """Add a message to a conversation. Returns message ID."""
    msg_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    with engine.connect() as conn:
        conn.execute(messages.insert().values(
            id=msg_id,
            conversation_id=conversation_id,
            role=role,
            content=content,
            sources=json.dumps(sources) if sources else None,
            created_at=now,
        ))
        # Update conversation's updated_at
        conn.execute(
            conversations.update()
            .where(conversations.c.id == conversation_id)
            .values(updated_at=now)
        )
        conn.commit()
    return msg_id


def set_title(engine: Engine, convo_id: str, title: str) -> None:
    """Set the title of a conversation (used for auto-titling)."""
    with engine.connect() as conn:
        conn.execute(
            conversations.update()
            .where(conversations.c.id == convo_id)
            .values(title=title)
        )
        conn.commit()


def get_recent_messages(
    engine: Engine,
    conversation_id: str,
    tenant_id: str | None = None,
    limit: int = 20,
) -> list[dict]:
    """Get the most recent messages for a conversation, in chronological order."""
    with engine.connect() as conn:
        query = (
            select(messages)
            .where(messages.c.conversation_id == conversation_id)
        )
        if tenant_id:
            query = query.join(
                conversations, messages.c.conversation_id == conversations.c.id
            ).where(conversations.c.tenant_id == tenant_id)
        rows = conn.execute(
            query.order_by(desc(messages.c.created_at)).limit(limit)
        ).fetchall()
    result = [
        {
            "id": r.id,
            "role": r.role,
            "content": r.content,
            "sources": json.loads(r.sources) if r.sources else None,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in reversed(rows)
    ]
    return result
