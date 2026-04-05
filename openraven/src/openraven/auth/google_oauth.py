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
