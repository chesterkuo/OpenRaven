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


# Paths accessible to demo sessions (exact match or prefix with / boundary)
_DEMO_ALLOWED_EXACT = {"/api/ask"}
_DEMO_ALLOWED_PREFIXES = (
    "/api/graph/",
    "/api/graph",
    "/api/wiki/",
    "/api/wiki",
    "/api/documents/",
    "/api/documents",
    "/api/conversations/",
    "/api/conversations",
    "/api/demo/",
    "/api/auth/demo",
    "/api/auth/logout",
    "/api/discovery",
    "/api/status",
    "/api/config/",
    "/api/health/",
)


def is_demo_allowed(path: str) -> bool:
    """Check if a path is accessible to demo sessions."""
    if path in _DEMO_ALLOWED_EXACT:
        return True
    return any(path.startswith(prefix) for prefix in _DEMO_ALLOWED_PREFIXES)
