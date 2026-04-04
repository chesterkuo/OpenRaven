from __future__ import annotations

import json
from pathlib import Path

import pytest


def test_google_auth_build_flow(tmp_path) -> None:
    from openraven.connectors.google_auth import build_auth_url
    url = build_auth_url(
        client_id="test-id",
        scopes=["https://www.googleapis.com/auth/drive.readonly"],
    )
    assert "accounts.google.com" in url
    assert "test-id" in url
    assert "drive.readonly" in url


def test_google_auth_token_save_load(tmp_path) -> None:
    from openraven.connectors.google_auth import save_token, load_token
    token_path = tmp_path / "token.json"
    token_data = {"access_token": "abc", "refresh_token": "xyz", "token_uri": "https://oauth2.googleapis.com/token"}

    save_token(token_data, token_path)
    assert token_path.exists()

    loaded = load_token(token_path)
    assert loaded["access_token"] == "abc"
    assert loaded["refresh_token"] == "xyz"


def test_google_auth_load_missing_token(tmp_path) -> None:
    from openraven.connectors.google_auth import load_token
    result = load_token(tmp_path / "nonexistent.json")
    assert result is None


def test_google_auth_scopes() -> None:
    from openraven.connectors.google_auth import DRIVE_SCOPES, GMAIL_SCOPES
    assert "drive.readonly" in DRIVE_SCOPES[0]
    assert "gmail.readonly" in GMAIL_SCOPES[0]
