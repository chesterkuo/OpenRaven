"""Conversation API routes."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import Engine

from openraven.auth.sessions import validate_session
from openraven.conversations.models import (
    create_conversation, list_conversations, get_conversation,
    delete_conversation, get_recent_messages,
)


class CreateConversationRequest(BaseModel):
    title: str | None = None


def _get_auth(request: Request, engine: Engine):
    """Extract auth context from session cookie."""
    session_id = request.cookies.get("session_id")
    if not session_id:
        raise HTTPException(401, "Not authenticated")
    ctx = validate_session(engine, session_id)
    if not ctx:
        raise HTTPException(401, "Session expired")
    return ctx, session_id


def create_conversations_router(engine: Engine) -> APIRouter:
    router = APIRouter(prefix="/api/conversations")

    @router.post("")
    async def create(request: Request, req: CreateConversationRequest):
        ctx, session_id = _get_auth(request, engine)
        if ctx.is_demo:
            existing = list_conversations(engine, tenant_id=ctx.tenant_id, session_id=session_id)
            if len(existing) >= 5:
                raise HTTPException(429, "Demo limited to 5 conversations")
        convo_id = create_conversation(
            engine,
            tenant_id=ctx.tenant_id,
            user_id=ctx.user_id,
            title=req.title,
            session_id=session_id if ctx.is_demo else None,
            demo_theme=ctx.demo_theme,
        )
        return {"id": convo_id}

    @router.get("")
    async def list_all(request: Request):
        ctx, session_id = _get_auth(request, engine)
        if ctx.is_demo:
            return list_conversations(engine, tenant_id=ctx.tenant_id, session_id=session_id)
        return list_conversations(engine, tenant_id=ctx.tenant_id, user_id=ctx.user_id)

    @router.get("/{convo_id}")
    async def get(request: Request, convo_id: str):
        ctx, _ = _get_auth(request, engine)
        convo = get_conversation(engine, convo_id, tenant_id=ctx.tenant_id)
        if not convo:
            raise HTTPException(404, "Conversation not found")
        msgs = get_recent_messages(engine, convo_id, limit=200)
        return {**convo, "messages": msgs}

    @router.delete("/{convo_id}")
    async def remove(request: Request, convo_id: str):
        ctx, _ = _get_auth(request, engine)
        convo = get_conversation(engine, convo_id, tenant_id=ctx.tenant_id)
        if not convo:
            raise HTTPException(404, "Conversation not found")
        delete_conversation(engine, convo_id, tenant_id=ctx.tenant_id)
        return {"ok": True}

    return router
