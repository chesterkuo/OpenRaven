# M3: Google Drive + Gmail Connectors Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let users connect their Google Drive and Gmail accounts to automatically ingest documents and emails into their knowledge base — the first external data connectors.

**Architecture:** A shared Google OAuth2 layer handles authentication. Two connector modules (`gdrive.py`, `gmail.py`) each implement a `sync()` coroutine that fetches documents, writes them to temp files, and feeds them into the existing `pipeline.add_files()`. OAuth tokens are stored as JSON at `config.working_dir/google_token.json`. New API endpoints handle the OAuth flow (redirect-based) and sync triggers. A new ConnectorsPage in the UI shows connection status, authorize buttons, and sync controls.

**Tech Stack:**
- Python: `google-auth-oauthlib`, `google-api-python-client` (new deps)
- Google APIs: Drive API v3, Gmail API v1
- OAuth2: installed-app flow (redirect to localhost callback)
- No cloud infrastructure needed — runs entirely local

**PRD Alignment:**
- M3 acceptance: "Google Drive 連接" (line 726)
- Feature table: Google Drive P1 (commercial), Gmail/Outlook P1 (commercial)
- Both are Personal+ tier features (line 623-624)

**Scope note:** Outlook connector is deferred — Gmail covers the email use case for M3. Outlook can follow the same pattern later with Microsoft Graph API.

---

## File Structure

### Python backend (openraven/)

| File | Action | Responsibility |
|---|---|---|
| `pyproject.toml` | Modify | Add google-auth-oauthlib, google-api-python-client |
| `src/openraven/config.py` | Modify | Add google_client_id, google_client_secret fields |
| `src/openraven/connectors/__init__.py` | Create | Package init |
| `src/openraven/connectors/google_auth.py` | Create | Shared OAuth2 flow: authorize, token refresh, credential loading |
| `src/openraven/connectors/gdrive.py` | Create | Drive API: list files, download, sync to pipeline |
| `src/openraven/connectors/gmail.py` | Create | Gmail API: list messages, extract text, sync to pipeline |
| `src/openraven/api/server.py` | Modify | Add connector OAuth + sync endpoints |
| `tests/test_connectors.py` | Create | Unit tests for auth, gdrive, gmail modules |
| `tests/test_api.py` | Modify | API endpoint tests |
| `.env.example` | Modify | Document Google OAuth credentials |

### TypeScript frontend (openraven-ui/)

| File | Action | Responsibility |
|---|---|---|
| `src/pages/ConnectorsPage.tsx` | Create | Google Drive + Gmail connection UI |
| `src/App.tsx` | Modify | Add /connectors route + nav link |
| `server/index.ts` | Modify | Add connectors proxy route |

---

## Task 1: Dependencies + Config — Google OAuth fields

**Files:**
- Modify: `openraven/pyproject.toml`
- Modify: `openraven/src/openraven/config.py`
- Modify: `openraven/tests/test_config.py`

- [ ] **Step 1: Write failing test**

Add to `openraven/tests/test_config.py`:

```python
def test_google_oauth_config_fields(tmp_path) -> None:
    config = RavenConfig(working_dir=tmp_path / "kb")
    assert config.google_client_id == ""
    assert config.google_client_secret == ""
    assert config.google_token_path == config.working_dir / "google_token.json"


def test_google_oauth_env_overrides(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "test-id-123")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "test-secret-456")
    config = RavenConfig(working_dir=tmp_path / "kb")
    assert config.google_client_id == "test-id-123"
    assert config.google_client_secret == "test-secret-456"
```

- [ ] **Step 2: Run to verify failure**

Run: `cd openraven && .venv/bin/python -m pytest tests/test_config.py -v -k "google"`

- [ ] **Step 3: Add config fields**

Add to `openraven/src/openraven/config.py` in `RavenConfig`:

```python
google_client_id: str = field(default_factory=lambda: os.environ.get("GOOGLE_CLIENT_ID", ""))
google_client_secret: str = field(default_factory=lambda: os.environ.get("GOOGLE_CLIENT_SECRET", ""))
```

Add property:

```python
@property
def google_token_path(self) -> Path:
    return self.working_dir / "google_token.json"
```

- [ ] **Step 4: Add dependencies to pyproject.toml**

Add to `[project] dependencies` in `openraven/pyproject.toml`:

```
"google-auth>=2.0.0",
"google-auth-oauthlib>=1.0.0",
"google-api-python-client>=2.0.0",
```

Then install: `cd openraven && .venv/bin/pip install -e .`

- [ ] **Step 5: Run tests**

Run: `cd openraven && .venv/bin/python -m pytest tests/ -v --ignore=tests/test_integration.py`

- [ ] **Step 6: Commit**

```bash
git add openraven/pyproject.toml openraven/src/openraven/config.py openraven/tests/test_config.py
git commit -m "feat(config): add Google OAuth fields and install google-api dependencies"
```

---

## Task 2: Shared Google OAuth2 module

**Files:**
- Create: `openraven/src/openraven/connectors/__init__.py`
- Create: `openraven/src/openraven/connectors/google_auth.py`
- Create: `openraven/tests/test_connectors.py`

- [ ] **Step 1: Write failing tests**

Create `openraven/tests/test_connectors.py`:

```python
from __future__ import annotations

import json
from pathlib import Path

import pytest


def test_google_auth_build_flow(tmp_path) -> None:
    from openraven.connectors.google_auth import build_auth_url
    url = build_auth_url(
        client_id="test-id",
        client_secret="test-secret",
        scopes=["https://www.googleapis.com/auth/drive.readonly"],
        redirect_port=8742,
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
```

- [ ] **Step 2: Create package**

Create `openraven/src/openraven/connectors/__init__.py`:

```python
```

- [ ] **Step 3: Create google_auth.py**

Create `openraven/src/openraven/connectors/google_auth.py`:

```python
from __future__ import annotations

import json
import logging
from pathlib import Path
from urllib.parse import urlencode

logger = logging.getLogger(__name__)

DRIVE_SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]
GMAIL_SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
ALL_SCOPES = DRIVE_SCOPES + GMAIL_SCOPES


def build_auth_url(
    client_id: str,
    client_secret: str,
    scopes: list[str],
    redirect_port: int = 8742,
) -> str:
    """Build the Google OAuth2 authorization URL."""
    params = {
        "client_id": client_id,
        "redirect_uri": f"http://localhost:{redirect_port}/callback",
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
    redirect_port: int = 8742,
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
                "redirect_uri": f"http://localhost:{redirect_port}/callback",
                "grant_type": "authorization_code",
            },
        )
        response.raise_for_status()
        return response.json()


def save_token(token_data: dict, token_path: Path) -> None:
    """Save OAuth token to disk."""
    token_path.write_text(json.dumps(token_data, indent=2), encoding="utf-8")
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
```

- [ ] **Step 4: Run tests**

Run: `cd openraven && .venv/bin/python -m pytest tests/test_connectors.py -v`

- [ ] **Step 5: Commit**

```bash
git add openraven/src/openraven/connectors/ openraven/tests/test_connectors.py
git commit -m "feat(connectors): add shared Google OAuth2 module"
```

---

## Task 3: Google Drive connector

**Files:**
- Create: `openraven/src/openraven/connectors/gdrive.py`
- Modify: `openraven/tests/test_connectors.py`

- [ ] **Step 1: Write failing tests**

Add to `openraven/tests/test_connectors.py`:

```python
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
    # Without credentials, should return empty list
    result = await sync_drive(credentials=None, output_dir=Path("/tmp"), max_files=10)
    assert result == []
```

- [ ] **Step 2: Create gdrive.py**

Create `openraven/src/openraven/connectors/gdrive.py`:

```python
from __future__ import annotations

import logging
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)

SUPPORTED_MIMETYPES = {
    "application/pdf": ".pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation": ".pptx",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx",
    "text/plain": ".txt",
    "text/html": ".html",
    "text/markdown": ".md",
}

# Google Docs/Sheets/Slides export as their Office equivalents
EXPORT_MIMETYPES = {
    "application/vnd.google-apps.document": ("application/vnd.openxmlformats-officedocument.wordprocessingml.document", ".docx"),
    "application/vnd.google-apps.presentation": ("application/vnd.openxmlformats-officedocument.presentationml.presentation", ".pptx"),
    "application/vnd.google-apps.spreadsheet": ("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", ".xlsx"),
}


def file_id_to_record_path(file_id: str) -> str:
    """Create a stable record path for a Drive file."""
    return f"gdrive://{file_id}"


async def sync_drive(
    credentials,
    output_dir: Path,
    max_files: int = 100,
) -> list[Path]:
    """Sync files from Google Drive to local temp directory.

    Returns list of local file paths ready for pipeline.add_files().
    """
    if credentials is None:
        return []

    import asyncio
    from googleapiclient.discovery import build

    def _list_and_download():
        service = build("drive", "v3", credentials=credentials)
        downloaded = []

        # List files, sorted by most recently modified
        query = " or ".join(f"mimeType='{mt}'" for mt in list(SUPPORTED_MIMETYPES) + list(EXPORT_MIMETYPES))
        results = service.files().list(
            q=query,
            pageSize=max_files,
            orderBy="modifiedTime desc",
            fields="files(id, name, mimeType, md5Checksum, modifiedTime)",
        ).execute()

        files = results.get("files", [])
        output_dir.mkdir(parents=True, exist_ok=True)

        for file_info in files:
            try:
                file_id = file_info["id"]
                name = file_info["name"]
                mime = file_info["mimeType"]

                if mime in EXPORT_MIMETYPES:
                    export_mime, ext = EXPORT_MIMETYPES[mime]
                    content = service.files().export(fileId=file_id, mimeType=export_mime).execute()
                elif mime in SUPPORTED_MIMETYPES:
                    ext = SUPPORTED_MIMETYPES[mime]
                    content = service.files().get_media(fileId=file_id).execute()
                else:
                    continue

                safe_name = name.replace("/", "_")
                if not safe_name.endswith(ext):
                    safe_name += ext
                dest = output_dir / safe_name
                dest.write_bytes(content if isinstance(content, bytes) else content.encode("utf-8"))
                downloaded.append(dest)
                logger.info(f"Downloaded Drive file: {name} ({file_id})")
            except Exception as e:
                logger.warning(f"Failed to download Drive file {file_info.get('name', '?')}: {e}")

        return downloaded

    return await asyncio.to_thread(_list_and_download)
```

- [ ] **Step 3: Run tests**

Run: `cd openraven && .venv/bin/python -m pytest tests/test_connectors.py -v`

- [ ] **Step 4: Commit**

```bash
git add openraven/src/openraven/connectors/gdrive.py openraven/tests/test_connectors.py
git commit -m "feat(connectors): add Google Drive sync module"
```

---

## Task 4: Gmail connector

**Files:**
- Create: `openraven/src/openraven/connectors/gmail.py`
- Modify: `openraven/tests/test_connectors.py`

- [ ] **Step 1: Write failing tests**

Add to `openraven/tests/test_connectors.py`:

```python
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
```

- [ ] **Step 2: Create gmail.py**

Create `openraven/src/openraven/connectors/gmail.py`:

```python
from __future__ import annotations

import base64
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def message_id_to_record_path(message_id: str) -> str:
    """Create a stable record path for a Gmail message."""
    return f"gmail://{message_id}"


def message_to_markdown(subject: str, sender: str, date: str, body: str) -> str:
    """Convert an email message to markdown format."""
    return f"# {subject}\n\n**From:** {sender}\n**Date:** {date}\n\n{body}"


async def sync_gmail(
    credentials,
    output_dir: Path,
    max_messages: int = 50,
) -> list[Path]:
    """Sync recent Gmail messages to local markdown files.

    Returns list of local file paths ready for pipeline.add_files().
    """
    if credentials is None:
        return []

    import asyncio
    from googleapiclient.discovery import build

    def _list_and_download():
        service = build("gmail", "v1", credentials=credentials)
        downloaded = []

        output_dir.mkdir(parents=True, exist_ok=True)

        # List recent messages
        results = service.users().messages().list(
            userId="me", maxResults=max_messages,
        ).execute()

        messages = results.get("messages", [])

        for msg_stub in messages:
            try:
                msg = service.users().messages().get(
                    userId="me", id=msg_stub["id"], format="full",
                ).execute()

                headers = {h["name"].lower(): h["value"] for h in msg["payload"]["headers"]}
                subject = headers.get("subject", "(no subject)")
                sender = headers.get("from", "unknown")
                date = headers.get("date", "")

                # Extract body text
                body = _extract_body(msg["payload"])
                if not body or len(body.strip()) < 20:
                    continue

                md = message_to_markdown(subject=subject, sender=sender, date=date, body=body)
                safe_name = subject.replace("/", "_").replace("\\", "_")[:80].strip()
                dest = output_dir / f"{safe_name}.md"
                dest.write_text(md, encoding="utf-8")
                downloaded.append(dest)
                logger.info(f"Downloaded Gmail: {subject} ({msg_stub['id']})")
            except Exception as e:
                logger.warning(f"Failed to process Gmail message {msg_stub.get('id', '?')}: {e}")

        return downloaded

    return await asyncio.to_thread(_list_and_download)


def _extract_body(payload: dict) -> str:
    """Extract plain text body from Gmail payload, handling multipart."""
    if payload.get("mimeType") == "text/plain" and payload.get("body", {}).get("data"):
        return base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8", errors="replace")

    for part in payload.get("parts", []):
        if part.get("mimeType") == "text/plain" and part.get("body", {}).get("data"):
            return base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8", errors="replace")
        # Recurse into nested multipart
        if part.get("parts"):
            result = _extract_body(part)
            if result:
                return result

    return ""
```

- [ ] **Step 3: Run tests**

Run: `cd openraven && .venv/bin/python -m pytest tests/test_connectors.py -v`

- [ ] **Step 4: Commit**

```bash
git add openraven/src/openraven/connectors/gmail.py openraven/tests/test_connectors.py
git commit -m "feat(connectors): add Gmail sync module"
```

---

## Task 5: API endpoints — OAuth flow + sync triggers

**Files:**
- Modify: `openraven/src/openraven/api/server.py`
- Modify: `openraven/tests/test_api.py`

- [ ] **Step 1: Write failing tests**

Add to `openraven/tests/test_api.py`:

```python
def test_connectors_status_endpoint(client: TestClient) -> None:
    response = client.get("/api/connectors/status")
    assert response.status_code == 200
    data = response.json()
    assert "gdrive" in data
    assert "gmail" in data
    assert data["gdrive"]["connected"] is False
    assert data["gmail"]["connected"] is False


def test_connectors_auth_url_requires_credentials(client: TestClient) -> None:
    response = client.get("/api/connectors/google/auth-url")
    # Should fail if no client_id configured
    assert response.status_code in (200, 400)


def test_connectors_sync_requires_auth(client: TestClient) -> None:
    response = client.post("/api/connectors/gdrive/sync")
    assert response.status_code == 401
```

- [ ] **Step 2: Implement connector endpoints**

Add inside `create_app()` in `server.py`:

```python
@app.get("/api/connectors/status")
async def connectors_status():
    from openraven.connectors.google_auth import load_token
    token = load_token(config.google_token_path)
    connected = token is not None
    return {
        "gdrive": {"connected": connected},
        "gmail": {"connected": connected},
        "google_configured": bool(config.google_client_id),
    }

@app.get("/api/connectors/google/auth-url")
async def google_auth_url():
    from fastapi.responses import JSONResponse
    if not config.google_client_id:
        return JSONResponse({"error": "GOOGLE_CLIENT_ID not configured"}, status_code=400)
    from openraven.connectors.google_auth import build_auth_url, ALL_SCOPES
    url = build_auth_url(
        client_id=config.google_client_id,
        client_secret=config.google_client_secret,
        scopes=ALL_SCOPES,
    )
    return {"auth_url": url}

@app.get("/api/connectors/google/callback")
async def google_callback(code: str):
    from openraven.connectors.google_auth import exchange_code, save_token
    token_data = await exchange_code(
        code=code,
        client_id=config.google_client_id,
        client_secret=config.google_client_secret,
    )
    save_token(token_data, config.google_token_path)
    return {"status": "connected"}

@app.post("/api/connectors/gdrive/sync")
async def gdrive_sync():
    from fastapi.responses import JSONResponse
    from openraven.connectors.google_auth import get_credentials
    from openraven.connectors.gdrive import sync_drive
    creds = get_credentials(config.google_token_path, config.google_client_id, config.google_client_secret)
    if not creds:
        return JSONResponse({"error": "Not authenticated. Connect Google account first."}, status_code=401)
    files = await sync_drive(credentials=creds, output_dir=config.ingestion_dir)
    if files:
        result = await pipeline.add_files(files)
        return {
            "files_synced": len(files),
            "entities_extracted": result.entities_extracted,
            "articles_generated": result.articles_generated,
            "errors": result.errors,
        }
    return {"files_synced": 0, "entities_extracted": 0, "articles_generated": 0, "errors": []}

@app.post("/api/connectors/gmail/sync")
async def gmail_sync():
    from fastapi.responses import JSONResponse
    from openraven.connectors.google_auth import get_credentials
    from openraven.connectors.gmail import sync_gmail
    creds = get_credentials(config.google_token_path, config.google_client_id, config.google_client_secret)
    if not creds:
        return JSONResponse({"error": "Not authenticated. Connect Google account first."}, status_code=401)
    files = await sync_gmail(credentials=creds, output_dir=config.ingestion_dir)
    if files:
        result = await pipeline.add_files(files)
        return {
            "files_synced": len(files),
            "entities_extracted": result.entities_extracted,
            "articles_generated": result.articles_generated,
            "errors": result.errors,
        }
    return {"files_synced": 0, "entities_extracted": 0, "articles_generated": 0, "errors": []}
```

- [ ] **Step 3: Run tests**

Run: `cd openraven && .venv/bin/python -m pytest tests/test_api.py -v -k "connector"`

- [ ] **Step 4: Run all tests**

Run: `cd openraven && .venv/bin/python -m pytest tests/ -v --ignore=tests/test_integration.py`

- [ ] **Step 5: Commit**

```bash
git add openraven/src/openraven/api/server.py openraven/tests/test_api.py
git commit -m "feat(api): add Google Drive and Gmail connector endpoints"
```

---

## Task 6: ConnectorsPage UI

**Files:**
- Create: `openraven-ui/src/pages/ConnectorsPage.tsx`
- Modify: `openraven-ui/src/App.tsx`
- Modify: `openraven-ui/server/index.ts`

- [ ] **Step 1: Create ConnectorsPage.tsx**

Create `openraven-ui/src/pages/ConnectorsPage.tsx`:

```tsx
import { useEffect, useState } from "react";

interface ConnectorStatus {
  gdrive: { connected: boolean };
  gmail: { connected: boolean };
  google_configured: boolean;
}

interface SyncResult {
  files_synced: number;
  entities_extracted: number;
  articles_generated: number;
  errors: string[];
}

export default function ConnectorsPage() {
  const [status, setStatus] = useState<ConnectorStatus | null>(null);
  const [syncing, setSyncing] = useState<string | null>(null);
  const [result, setResult] = useState<SyncResult | null>(null);

  useEffect(() => {
    fetch("/api/connectors/status").then(r => r.json()).then(setStatus).catch(() => {});
  }, []);

  async function handleConnect() {
    const res = await fetch("/api/connectors/google/auth-url");
    const data = await res.json();
    if (data.auth_url) {
      window.open(data.auth_url, "_blank", "width=500,height=600");
    }
  }

  async function handleSync(connector: "gdrive" | "gmail") {
    setSyncing(connector);
    setResult(null);
    try {
      const res = await fetch(`/api/connectors/${connector}/sync`, { method: "POST" });
      setResult(await res.json());
    } catch {
      setResult({ files_synced: 0, entities_extracted: 0, articles_generated: 0, errors: ["Sync failed"] });
    } finally {
      setSyncing(null);
    }
  }

  if (!status) return <div className="text-gray-500">Loading...</div>;

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Connectors</h1>

      {!status.google_configured && (
        <div className="bg-amber-950/30 border border-amber-700 rounded-lg p-4 mb-6 text-sm text-amber-300">
          Google OAuth not configured. Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in .env to enable connectors.
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
        {/* Google Drive */}
        <div className="bg-gray-900 border border-gray-800 rounded-lg p-4">
          <div className="flex items-center justify-between mb-3">
            <h2 className="font-semibold">Google Drive</h2>
            <span className={`text-xs px-2 py-0.5 rounded ${status.gdrive.connected ? "bg-green-900 text-green-400" : "bg-gray-800 text-gray-500"}`}>
              {status.gdrive.connected ? "Connected" : "Not connected"}
            </span>
          </div>
          <p className="text-sm text-gray-400 mb-3">Import documents from your Google Drive (PDF, Docs, Sheets, Slides).</p>
          {!status.gdrive.connected ? (
            <button onClick={handleConnect} disabled={!status.google_configured} className="text-sm px-3 py-1.5 rounded bg-blue-600 text-white hover:bg-blue-500 disabled:bg-gray-700 disabled:text-gray-500">
              Connect Google Account
            </button>
          ) : (
            <button onClick={() => handleSync("gdrive")} disabled={syncing !== null} className="text-sm px-3 py-1.5 rounded bg-gray-700 text-gray-200 hover:bg-gray-600 disabled:opacity-50">
              {syncing === "gdrive" ? "Syncing..." : "Sync Now"}
            </button>
          )}
        </div>

        {/* Gmail */}
        <div className="bg-gray-900 border border-gray-800 rounded-lg p-4">
          <div className="flex items-center justify-between mb-3">
            <h2 className="font-semibold">Gmail</h2>
            <span className={`text-xs px-2 py-0.5 rounded ${status.gmail.connected ? "bg-green-900 text-green-400" : "bg-gray-800 text-gray-500"}`}>
              {status.gmail.connected ? "Connected" : "Not connected"}
            </span>
          </div>
          <p className="text-sm text-gray-400 mb-3">Import emails from your Gmail account as knowledge base entries.</p>
          {!status.gmail.connected ? (
            <button onClick={handleConnect} disabled={!status.google_configured} className="text-sm px-3 py-1.5 rounded bg-blue-600 text-white hover:bg-blue-500 disabled:bg-gray-700 disabled:text-gray-500">
              Connect Google Account
            </button>
          ) : (
            <button onClick={() => handleSync("gmail")} disabled={syncing !== null} className="text-sm px-3 py-1.5 rounded bg-gray-700 text-gray-200 hover:bg-gray-600 disabled:opacity-50">
              {syncing === "gmail" ? "Syncing..." : "Sync Now"}
            </button>
          )}
        </div>
      </div>

      {result && (
        <div className="bg-gray-900 border border-gray-800 rounded-lg p-4">
          <h2 className="font-semibold mb-2">Sync Results</h2>
          <div className="grid grid-cols-3 gap-4 text-center">
            <div><div className="text-2xl font-bold text-blue-400">{result.files_synced}</div><div className="text-xs text-gray-500">Files synced</div></div>
            <div><div className="text-2xl font-bold text-green-400">{result.entities_extracted}</div><div className="text-xs text-gray-500">Entities</div></div>
            <div><div className="text-2xl font-bold text-purple-400">{result.articles_generated}</div><div className="text-xs text-gray-500">Articles</div></div>
          </div>
          {result.errors.length > 0 && <div className="mt-3 text-red-400 text-sm">{result.errors.map((e, i) => <div key={i}>{e}</div>)}</div>}
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Add route to App.tsx**

Add import:
```tsx
import ConnectorsPage from "./pages/ConnectorsPage";
```

Add nav link (after Wiki, before Status):
```tsx
<NavLink to="/connectors" className={({ isActive }) => isActive ? "text-blue-400" : "text-gray-400 hover:text-gray-200"}>Connectors</NavLink>
```

Add route:
```tsx
<Route path="/connectors" element={<ConnectorsPage />} />
```

- [ ] **Step 3: Add connector proxy to Hono index.ts**

Add to `openraven-ui/server/index.ts`, in the proxy section:

```typescript
app.all("/api/connectors/*", async (c) => {
  try {
    const url = `${CORE_API_URL}${c.req.path}${c.req.url.includes("?") ? "?" + c.req.url.split("?")[1] : ""}`;
    const res = await fetch(url, { method: c.req.method });
    const data = await res.json();
    return c.json(data, res.status as any);
  } catch (e) {
    return c.json({ error: `Core engine error: ${(e as Error).message}` }, 502);
  }
});
```

- [ ] **Step 4: Build and test**

```bash
cd openraven-ui && bun test tests/ && bun run build
```

- [ ] **Step 5: Commit**

```bash
git add openraven-ui/src/pages/ConnectorsPage.tsx openraven-ui/src/App.tsx openraven-ui/server/index.ts
git commit -m "feat(ui): add ConnectorsPage with Google Drive and Gmail sync UI"
```

---

## Task 7: Update .env.example + E2E verification

- [ ] **Step 1: Update .env.example**

Add to `openraven/.env.example`:

```bash
# === Google Connectors (M3) ===
# Create OAuth credentials at https://console.cloud.google.com/apis/credentials
# GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
# GOOGLE_CLIENT_SECRET=your-client-secret
```

- [ ] **Step 2: Run full test suite**

```bash
cd openraven && .venv/bin/python -m pytest tests/ -v --ignore=tests/test_integration.py
cd openraven-ui && bun test tests/ && bun run build
```

- [ ] **Step 3: Restart PM2 and verify**

```bash
pm2 restart all && sleep 10
curl -sf http://localhost:8741/api/connectors/status | python3 -m json.tool
```

- [ ] **Step 4: Commit**

```bash
git add openraven/.env.example
git commit -m "docs: add Google connector OAuth config to .env.example"
```

---

## Summary

| Task | What | Tests Added |
|---|---|---|
| 1 | Config: Google OAuth fields + dependencies | 2 config tests |
| 2 | Shared Google OAuth2 module | 4 auth tests |
| 3 | Google Drive connector | 3 drive tests |
| 4 | Gmail connector | 3 gmail tests |
| 5 | API: connector endpoints | 3 API tests |
| 6 | ConnectorsPage UI | Build check |
| 7 | .env.example + E2E verify | Full suite |

**Total new tests: 15**

**Note:** Full E2E testing requires Google Cloud Console OAuth credentials. The unit tests verify module structure and function signatures without live Google API calls.
