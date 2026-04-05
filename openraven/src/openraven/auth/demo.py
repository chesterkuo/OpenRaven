"""Demo session routes — theme listing and anonymous session creation."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel
from sqlalchemy import Engine, select, delete as sa_delete

from openraven.auth.db import sessions as sessions_table, conversations
from openraven.auth.sessions import create_demo_session


class DemoStartRequest(BaseModel):
    theme: str


class ThemeInfo(BaseModel):
    slug: str
    name: str
    description: str


def _list_themes(tenants_root: Path) -> list[ThemeInfo]:
    """Scan the demo tenant directory for theme sub-directories."""
    demo_dir = tenants_root / "demo"
    if not demo_dir.is_dir():
        return []
    themes: list[ThemeInfo] = []
    for child in sorted(demo_dir.iterdir()):
        if not child.is_dir():
            continue
        meta_path = child / ".theme.json"
        if meta_path.exists():
            meta = json.loads(meta_path.read_text())
            themes.append(ThemeInfo(
                slug=child.name,
                name=meta.get("name", child.name),
                description=meta.get("description", ""),
            ))
        else:
            themes.append(ThemeInfo(slug=child.name, name=child.name, description=""))
    return themes


def create_demo_router(engine: Engine, tenants_root: Path = Path("/data/tenants")) -> APIRouter:
    router = APIRouter()

    @router.get("/api/demo/themes", response_model=list[ThemeInfo])
    async def list_themes():
        return _list_themes(tenants_root)

    @router.post("/api/auth/demo")
    async def start_demo(req: DemoStartRequest, response: Response):
        themes = _list_themes(tenants_root)
        valid_slugs = {t.slug for t in themes}
        if req.theme not in valid_slugs:
            raise HTTPException(404, f"Theme '{req.theme}' not found")
        session_id = create_demo_session(engine, theme=req.theme)
        response.set_cookie(
            "session_id", session_id,
            httponly=True, samesite="lax", secure=False,
            max_age=2 * 3600,
        )
        return {"theme": req.theme, "message": "Demo session started"}

    return router


def cleanup_expired_demo_sessions(engine: Engine) -> int:
    """Delete expired demo sessions and their associated conversations. Returns count deleted."""
    now = datetime.now(timezone.utc)
    with engine.connect() as conn:
        # Find expired demo sessions
        expired = conn.execute(
            select(sessions_table.c.id).where(
                sessions_table.c.is_demo == True,
                sessions_table.c.expires_at < now,
            )
        ).fetchall()
        expired_ids = [r.id for r in expired]

        if expired_ids:
            # Delete conversations linked to these sessions (messages cascade)
            conn.execute(
                sa_delete(conversations).where(
                    conversations.c.session_id.in_(expired_ids)
                )
            )
            # Delete the sessions themselves
            conn.execute(
                sa_delete(sessions_table).where(
                    sessions_table.c.id.in_(expired_ids)
                )
            )
            conn.commit()

    return len(expired_ids)
