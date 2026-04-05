"""Demo session routes — theme listing and anonymous session creation."""
from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel
from sqlalchemy import Engine

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
