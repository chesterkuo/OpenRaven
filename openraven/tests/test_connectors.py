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


def test_gmail_message_to_markdown() -> None:
    from openraven.connectors.gmail import message_to_markdown
    md = message_to_markdown(
        subject="Q1 Report Discussion",
        sender="alice@example.com",
        date="2026-01-15",
        body="The Q1 numbers look strong. Revenue up 15%.",
    )
    assert "Q1 Report Discussion" in md
    assert "alice@example.com" in md
    assert "Revenue up 15%" in md


def test_gmail_message_id_to_path() -> None:
    from openraven.connectors.gmail import message_id_to_record_path
    path = message_id_to_record_path("18b3f9a1c2d4e5f6")
    assert path == "gmail://18b3f9a1c2d4e5f6"


async def test_gmail_sync_requires_credentials() -> None:
    from openraven.connectors.gmail import sync_gmail
    result = await sync_gmail(credentials=None, output_dir=Path("/tmp"), max_messages=10)
    assert result == []


def test_meet_transcript_query() -> None:
    from openraven.connectors.gdrive import MEET_QUERY
    assert "Meeting transcript" in MEET_QUERY
    assert "google-apps.document" in MEET_QUERY


async def test_meet_sync_requires_credentials() -> None:
    from openraven.connectors.gdrive import sync_meet_transcripts
    result = await sync_meet_transcripts(credentials=None, output_dir=Path("/tmp"), max_files=10)
    assert result == []


def test_otter_transcript_to_markdown() -> None:
    from openraven.connectors.otter import transcript_to_markdown
    md = transcript_to_markdown(
        title="Q1 Planning Meeting",
        date="2026-03-15",
        speakers=[
            {"name": "Alice", "timestamp": "00:01:23", "text": "Let's review the Q1 roadmap."},
            {"name": "Bob", "timestamp": "00:02:05", "text": "I think we should prioritize the API redesign."},
        ],
    )
    assert "Q1 Planning Meeting" in md
    assert "Alice" in md
    assert "00:01:23" in md
    assert "Bob" in md
    assert "API redesign" in md


async def test_otter_sync_requires_api_key() -> None:
    from openraven.connectors.otter import sync_otter
    result = await sync_otter(api_key="", output_dir=Path("/tmp"), max_transcripts=10)
    assert result == []


def test_otter_key_save_load(tmp_path) -> None:
    from openraven.connectors.otter import save_api_key, load_api_key
    key_path = tmp_path / "otter_key"
    save_api_key("test-otter-key-123", key_path)
    assert key_path.exists()
    loaded = load_api_key(key_path)
    assert loaded == "test-otter-key-123"


def test_otter_key_load_missing(tmp_path) -> None:
    from openraven.connectors.otter import load_api_key
    result = load_api_key(tmp_path / "nonexistent")
    assert result == ""


def test_otter_key_permissions(tmp_path) -> None:
    import os
    import stat
    from openraven.connectors.otter import save_api_key
    key_path = tmp_path / "otter_key"
    save_api_key("secret", key_path)
    mode = stat.S_IMODE(os.stat(key_path).st_mode)
    assert mode == 0o600
