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


def test_gdrive_supported_mimetypes() -> None:
    from openraven.connectors.gdrive import SUPPORTED_MIMETYPES
    assert "application/pdf" in SUPPORTED_MIMETYPES
    assert "text/plain" in SUPPORTED_MIMETYPES


def test_gdrive_file_to_path_mapping() -> None:
    from openraven.connectors.gdrive import file_id_to_record_path
    path = file_id_to_record_path("1BxiMVs0XRA5nFMdK")
    assert path == "gdrive://1BxiMVs0XRA5nFMdK"


async def test_gdrive_download_file_requires_credentials() -> None:
    from openraven.connectors.gdrive import sync_drive
    result = await sync_drive(credentials=None, output_dir=Path("/tmp"), max_files=10)
    assert result == []
