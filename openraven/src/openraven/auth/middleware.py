"""FastAPI dependency for auth-protected routes."""

from fastapi import Request, HTTPException
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
