from __future__ import annotations

import json
import logging
from pathlib import Path
from urllib.parse import urlencode

logger = logging.getLogger(__name__)

DRIVE_SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]
GMAIL_SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
ALL_SCOPES = DRIVE_SCOPES + GMAIL_SCOPES

OAUTH_REDIRECT_URI = "http://localhost:8741/api/connectors/google/callback"


def build_auth_url(
    client_id: str,
    scopes: list[str],
) -> str:
    """Build the Google OAuth2 authorization URL."""
    params = {
        "client_id": client_id,
        "redirect_uri": OAUTH_REDIRECT_URI,
        "response_type": "code",
        "scope": " ".join(scopes),
        "access_type": "offline",
        "prompt": "consent",
    }
    return f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"


async def exchange_code(
    code: str,
    client_id: str,
    client_secret: str,
) -> dict:
    """Exchange authorization code for tokens."""
    import httpx
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": code,
                "client_id": client_id,
                "client_secret": client_secret,
                "redirect_uri": OAUTH_REDIRECT_URI,
                "grant_type": "authorization_code",
            },
        )
        response.raise_for_status()
        return response.json()


def save_token(token_data: dict, token_path: Path) -> None:
    """Save OAuth token to disk with restrictive permissions."""
    import os
    fd = os.open(str(token_path), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(json.dumps(token_data, indent=2))
    logger.info(f"Saved Google token to {token_path}")


def load_token(token_path: Path) -> dict | None:
    """Load OAuth token from disk. Returns None if not found."""
    if not token_path.exists():
        return None
    return json.loads(token_path.read_text(encoding="utf-8"))


def get_credentials(token_path: Path, client_id: str, client_secret: str):
    """Build google.oauth2.credentials.Credentials from saved token."""
    from google.oauth2.credentials import Credentials
    token_data = load_token(token_path)
    if not token_data:
        return None
    return Credentials(
        token=token_data.get("access_token"),
        refresh_token=token_data.get("refresh_token"),
        token_uri="https://oauth2.googleapis.com/token",
        client_id=client_id,
        client_secret=client_secret,
        scopes=token_data.get("scopes", ALL_SCOPES),
    )
