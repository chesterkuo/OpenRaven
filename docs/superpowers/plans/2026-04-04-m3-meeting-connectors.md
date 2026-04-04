# M3: Google Meet + Otter.ai Meeting Connectors Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add Google Meet transcript sync (via existing Drive API) and Otter.ai meeting note sync (via REST API with user-provided key) to complete the M3 PRD meeting connector requirement.

**Architecture:** Google Meet transcripts are Google Docs saved to Drive, so we extend the existing `gdrive.py` with a `sync_meet_transcripts()` function that filters by name pattern. Otter.ai is a new `otter.py` module using httpx to call the Otter.ai REST API, with API key stored locally. Both feed files into the existing `pipeline.add_files()`. The ConnectorsPage UI adds two new cards (Meet + Otter.ai) to the existing grid.

**Tech Stack:** Python (httpx, google-api-python-client), TypeScript/React (ConnectorsPage UI). No new dependencies.

---

## File Structure

| File | Action | Responsibility |
|---|---|---|
| `openraven/src/openraven/connectors/gdrive.py` | Modify | Add `MEET_QUERY`, `sync_meet_transcripts()` |
| `openraven/src/openraven/connectors/otter.py` | Create | `transcript_to_markdown()`, `sync_otter()`, `save_api_key()`, `load_api_key()` |
| `openraven/src/openraven/config.py` | Modify | Add `otter_key_path` property, `otter_api_key` property |
| `openraven/src/openraven/api/server.py` | Modify | Add Meet sync, Otter save-key + sync endpoints, update status |
| `openraven/tests/test_connectors.py` | Modify | Add Meet + Otter unit tests |
| `openraven/tests/test_api.py` | Modify | Add Meet + Otter endpoint tests |
| `openraven-ui/src/pages/ConnectorsPage.tsx` | Modify | Add Google Meet + Otter.ai cards |
| `openraven-ui/server/index.ts` | Modify | Fix proxy to forward POST request bodies |
| `openraven/.env.example` | Modify | Document Otter.ai setup |

---

## Task 1: Config — add Otter.ai key path

**Files:**
- Modify: `openraven/src/openraven/config.py`
- Modify: `openraven/tests/test_config.py`

- [ ] **Step 1: Write failing test**

Add to `openraven/tests/test_config.py`:

```python
def test_otter_key_path(tmp_path) -> None:
    config = RavenConfig(working_dir=tmp_path / "kb")
    assert config.otter_key_path == config.working_dir / "otter_api_key"


def test_otter_api_key_returns_empty_when_no_file(tmp_path) -> None:
    config = RavenConfig(working_dir=tmp_path / "kb")
    assert config.otter_api_key == ""
```

- [ ] **Step 2: Run to verify failure**

Run: `cd openraven && .venv/bin/python -m pytest tests/test_config.py -v -k "otter"`

- [ ] **Step 3: Add property**

Add to `RavenConfig` in `openraven/src/openraven/config.py`, after the `google_token_path` property:

```python
    @property
    def otter_key_path(self) -> Path:
        return self.working_dir / "otter_api_key"

    @property
    def otter_api_key(self) -> str:
        """Load Otter.ai API key from file. Returns empty string if not found."""
        if not self.otter_key_path.exists():
            return ""
        return self.otter_key_path.read_text(encoding="utf-8").strip()
```

- [ ] **Step 4: Run tests**

Run: `cd openraven && .venv/bin/python -m pytest tests/test_config.py -v`

- [ ] **Step 5: Commit**

```bash
git add openraven/src/openraven/config.py openraven/tests/test_config.py
git commit -m "feat(config): add otter_key_path property"
```

---

## Task 2: Google Meet transcript sync in gdrive.py

**Files:**
- Modify: `openraven/src/openraven/connectors/gdrive.py`
- Modify: `openraven/tests/test_connectors.py`

- [ ] **Step 1: Write failing tests**

Add to `openraven/tests/test_connectors.py`:

```python
def test_meet_transcript_query() -> None:
    from openraven.connectors.gdrive import MEET_QUERY
    assert "Meeting transcript" in MEET_QUERY
    assert "google-apps.document" in MEET_QUERY


async def test_meet_sync_requires_credentials() -> None:
    from openraven.connectors.gdrive import sync_meet_transcripts
    result = await sync_meet_transcripts(credentials=None, output_dir=Path("/tmp"), max_files=10)
    assert result == []
```

- [ ] **Step 2: Run to verify failure**

Run: `cd openraven && .venv/bin/python -m pytest tests/test_connectors.py -v -k "meet"`

- [ ] **Step 3: Implement sync_meet_transcripts**

Add to `openraven/src/openraven/connectors/gdrive.py`, after the existing `sync_drive` function:

```python
MEET_QUERY = "name contains 'Meeting transcript' and mimeType='application/vnd.google-apps.document'"


async def sync_meet_transcripts(
    credentials,
    output_dir: Path,
    max_files: int = 50,
) -> list[Path]:
    """Sync Google Meet transcripts from Drive to local directory.

    Meet transcripts are Google Docs saved with titles like
    'Meeting transcript - [meeting title]'.
    """
    if credentials is None:
        return []

    import asyncio
    from googleapiclient.discovery import build

    def _list_and_download():
        service = build("drive", "v3", credentials=credentials)
        downloaded = []

        results = (
            service.files()
            .list(
                q=MEET_QUERY,
                pageSize=max_files,
                orderBy="modifiedTime desc",
                fields="files(id, name, mimeType, modifiedTime)",
            )
            .execute()
        )

        files = results.get("files", [])
        output_dir.mkdir(parents=True, exist_ok=True)

        for file_info in files:
            try:
                file_id = file_info["id"]
                name = file_info["name"]

                # Export Google Doc as plain text
                content = (
                    service.files()
                    .export(fileId=file_id, mimeType="text/plain")
                    .execute()
                )

                safe_name = name.replace("/", "_").replace("\\", "_")[:80].strip()
                dest = output_dir / f"{safe_name}_{file_id[:8]}.txt"
                dest.write_bytes(
                    content if isinstance(content, bytes) else content.encode("utf-8")
                )
                downloaded.append(dest)
                logger.info(f"Downloaded Meet transcript: {name} ({file_id})")
            except Exception as e:
                logger.warning(f"Failed to download Meet transcript {file_info.get('name', '?')}: {e}")

        return downloaded

    return await asyncio.to_thread(_list_and_download)
```

- [ ] **Step 4: Run tests**

Run: `cd openraven && .venv/bin/python -m pytest tests/test_connectors.py -v`

- [ ] **Step 5: Commit**

```bash
git add openraven/src/openraven/connectors/gdrive.py openraven/tests/test_connectors.py
git commit -m "feat(connectors): add Google Meet transcript sync via Drive API"
```

---

## Task 3: Otter.ai connector module

**Files:**
- Create: `openraven/src/openraven/connectors/otter.py`
- Modify: `openraven/tests/test_connectors.py`

- [ ] **Step 1: Write failing tests**

Add to `openraven/tests/test_connectors.py`:

```python
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
```

- [ ] **Step 2: Run to verify failure**

Run: `cd openraven && .venv/bin/python -m pytest tests/test_connectors.py -v -k "otter"`

- [ ] **Step 3: Create otter.py**

Create `openraven/src/openraven/connectors/otter.py`:

```python
from __future__ import annotations

import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)


def transcript_to_markdown(title: str, date: str, speakers: list[dict]) -> str:
    """Convert an Otter.ai transcript to markdown format.

    Args:
        title: Meeting title
        date: Meeting date string
        speakers: List of dicts with 'name', 'text', and optional 'timestamp' keys
    """
    lines = [f"# {title}", f"\n**Date:** {date}\n"]
    for entry in speakers:
        ts = entry.get("timestamp", "")
        label = f"**{entry['name']} ({ts}):**" if ts else f"**{entry['name']}:**"
        lines.append(f"{label} {entry['text']}\n")
    return "\n".join(lines)


def save_api_key(api_key: str, key_path: Path) -> None:
    """Save Otter.ai API key to disk with restrictive permissions."""
    key_path.write_text(api_key.strip(), encoding="utf-8")
    os.chmod(key_path, 0o600)
    logger.info(f"Saved Otter.ai API key to {key_path}")


def load_api_key(key_path: Path) -> str:
    """Load Otter.ai API key from disk. Returns empty string if not found."""
    if not key_path.exists():
        return ""
    return key_path.read_text(encoding="utf-8").strip()


async def sync_otter(
    api_key: str,
    output_dir: Path,
    max_transcripts: int = 50,
) -> list[Path]:
    """Sync recent transcripts from Otter.ai API.

    Returns list of local file paths ready for pipeline.add_files().
    """
    if not api_key:
        return []

    import asyncio

    def _fetch_and_save():
        import httpx

        downloaded = []
        output_dir.mkdir(parents=True, exist_ok=True)

        # NOTE: Otter.ai API endpoints are based on their documented API.
        # If the API structure changes, update the base_url and endpoint paths.
        try:
            with httpx.Client(
                base_url="https://otter.ai/forward/api/v1",
                headers={"Authorization": f"Bearer {api_key}"},
                timeout=30,
            ) as client:
                # List recent speeches/transcripts
                response = client.get("/speeches", params={"page_size": max_transcripts})
                response.raise_for_status()
                data = response.json()

                speeches = data.get("speeches", data.get("results", []))

                for speech in speeches:
                    try:
                        speech_id = speech.get("otid", speech.get("id", ""))
                        title = speech.get("title", "Untitled Meeting")
                        created = speech.get("created_at", speech.get("start_time", ""))

                        # Fetch full transcript
                        detail_resp = client.get(f"/speeches/{speech_id}")
                        detail_resp.raise_for_status()
                        detail = detail_resp.json()

                        # Extract speaker segments with timestamps
                        transcripts = detail.get("transcripts", detail.get("segments", []))
                        speakers = []
                        for segment in transcripts:
                            speakers.append({
                                "name": segment.get("speaker", segment.get("speaker_name", "Speaker")),
                                "text": segment.get("text", segment.get("transcript", "")),
                                "timestamp": segment.get("timestamp", segment.get("start_time", "")),
                            })

                        if not speakers:
                            continue

                        md = transcript_to_markdown(title=title, date=created, speakers=speakers)
                        safe_name = title.replace("/", "_").replace("\\", "_")[:80].strip()
                        dest = output_dir / f"{safe_name}_{speech_id[:8]}.md"
                        dest.write_text(md, encoding="utf-8")
                        downloaded.append(dest)
                        logger.info(f"Downloaded Otter transcript: {title} ({speech_id})")
                    except Exception as e:
                        logger.warning(f"Failed to process Otter transcript {speech.get('title', '?')}: {e}")
        except Exception as e:
            logger.warning(f"Otter.ai API error: {e}")

        return downloaded

    return await asyncio.to_thread(_fetch_and_save)
```

- [ ] **Step 4: Run tests**

Run: `cd openraven && .venv/bin/python -m pytest tests/test_connectors.py -v`

- [ ] **Step 5: Commit**

```bash
git add openraven/src/openraven/connectors/otter.py openraven/tests/test_connectors.py
git commit -m "feat(connectors): add Otter.ai meeting transcript connector"
```

---

## Task 4: API endpoints — Meet sync + Otter save-key/sync

**Files:**
- Modify: `openraven/src/openraven/api/server.py`
- Modify: `openraven/tests/test_api.py`

- [ ] **Step 1: Write failing tests**

Add to `openraven/tests/test_api.py`:

```python
def test_connectors_status_includes_meet_and_otter(client: TestClient) -> None:
    response = client.get("/api/connectors/status")
    assert response.status_code == 200
    data = response.json()
    assert "meet" in data
    assert "otter" in data
    assert data["meet"]["connected"] is False
    assert data["otter"]["connected"] is False


def test_meet_sync_requires_auth(client: TestClient) -> None:
    response = client.post("/api/connectors/meet/sync")
    assert response.status_code == 401


def test_otter_save_key_endpoint(client: TestClient) -> None:
    response = client.post("/api/connectors/otter/save-key", json={"api_key": "test-key"})
    assert response.status_code == 200
    data = response.json()
    assert data["saved"] is True


def test_otter_sync_requires_key(client: TestClient) -> None:
    response = client.post("/api/connectors/otter/sync")
    assert response.status_code == 401
```

- [ ] **Step 2: Run to verify failure**

Run: `cd openraven && .venv/bin/python -m pytest tests/test_api.py -v -k "meet or otter"`

- [ ] **Step 3: Update connectors_status endpoint**

In `openraven/src/openraven/api/server.py`, update the `connectors_status` function to include meet and otter:

```python
    @app.get("/api/connectors/status")
    async def connectors_status():
        from openraven.connectors.google_auth import load_token
        token = load_token(config.google_token_path)
        google_connected = token is not None
        return {
            "gdrive": {"connected": google_connected},
            "gmail": {"connected": google_connected},
            "meet": {"connected": google_connected},
            "otter": {"connected": bool(config.otter_api_key)},
            "google_configured": bool(config.google_client_id and config.google_client_secret),
        }
```

- [ ] **Step 4: Add Meet sync endpoint**

Add after the `gmail_sync` endpoint in `server.py`:

```python
    @app.post("/api/connectors/meet/sync")
    async def meet_sync():
        from fastapi.responses import JSONResponse
        from openraven.connectors.gdrive import sync_meet_transcripts
        from openraven.connectors.google_auth import get_credentials
        creds = get_credentials(
            config.google_token_path, config.google_client_id, config.google_client_secret
        )
        if not creds:
            return JSONResponse(
                {"error": "Not authenticated. Connect Google account first."}, status_code=401
            )
        files = await sync_meet_transcripts(
            credentials=creds, output_dir=config.ingestion_dir / "meet"
        )
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

- [ ] **Step 5: Add Otter save-key and sync endpoints**

Add after the Meet sync endpoint:

```python
    @app.post("/api/connectors/otter/save-key")
    async def otter_save_key(body: dict):
        from openraven.connectors.otter import save_api_key
        api_key = body.get("api_key", "")
        if not api_key:
            from fastapi.responses import JSONResponse
            return JSONResponse({"error": "api_key is required"}, status_code=400)
        save_api_key(api_key, config.otter_key_path)
        return {"saved": True}

    @app.post("/api/connectors/otter/sync")
    async def otter_sync():
        from fastapi.responses import JSONResponse
        from openraven.connectors.otter import sync_otter
        api_key = config.otter_api_key
        if not api_key:
            return JSONResponse(
                {"error": "Otter.ai API key not configured. Save your key first."}, status_code=401
            )
        files = await sync_otter(
            api_key=api_key, output_dir=config.ingestion_dir / "otter"
        )
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

- [ ] **Step 6: Run tests**

Run: `cd openraven && .venv/bin/python -m pytest tests/test_api.py -v`

- [ ] **Step 7: Commit**

```bash
git add openraven/src/openraven/api/server.py openraven/tests/test_api.py
git commit -m "feat(api): add Google Meet and Otter.ai connector endpoints"
```

---

## Task 5: ConnectorsPage UI — add Meet + Otter cards

**Files:**
- Modify: `openraven-ui/src/pages/ConnectorsPage.tsx`

- [ ] **Step 1: Read ConnectorsPage.tsx**

Read `openraven-ui/src/pages/ConnectorsPage.tsx` to confirm current structure.

- [ ] **Step 2: Update ConnectorStatus interface**

Update the interface at the top:

```typescript
interface ConnectorStatus {
  gdrive: { connected: boolean };
  gmail: { connected: boolean };
  meet: { connected: boolean };
  otter: { connected: boolean };
  google_configured: boolean;
}
```

- [ ] **Step 3: Add Otter API key state and handlers**

Add state after existing state declarations:

```typescript
  const [otterKey, setOtterKey] = useState("");
  const [savingKey, setSavingKey] = useState(false);
```

Add handler after `handleSync`:

```typescript
  async function handleSaveOtterKey() {
    if (!otterKey.trim()) return;
    setSavingKey(true);
    try {
      await fetch("/api/connectors/otter/save-key", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ api_key: otterKey.trim() }),
      });
      const statusRes = await fetch("/api/connectors/status");
      setStatus(await statusRes.json());
      setOtterKey("");
    } catch { /* ignore */ }
    finally { setSavingKey(false); }
  }
```

- [ ] **Step 4: Update handleSync to accept new connector types**

Update the `handleSync` function signature:

```typescript
  async function handleSync(connector: "gdrive" | "gmail" | "meet" | "otter") {
```

- [ ] **Step 5: Add Google Meet card**

Add after the Gmail card `</div>`, inside the grid:

```tsx
        {/* Google Meet */}
        <div className="bg-gray-900 border border-gray-800 rounded-lg p-4">
          <div className="flex items-center justify-between mb-3">
            <h2 className="font-semibold">Google Meet</h2>
            <span className={`text-xs px-2 py-0.5 rounded ${status.meet.connected ? "bg-green-900 text-green-400" : "bg-gray-800 text-gray-500"}`}>
              {status.meet.connected ? "Connected" : "Not connected"}
            </span>
          </div>
          <p className="text-sm text-gray-400 mb-3">Import meeting transcripts from Google Meet.</p>
          {!status.meet.connected ? (
            <button onClick={handleConnect} disabled={!status.google_configured} className="text-sm px-3 py-1.5 rounded bg-blue-600 text-white hover:bg-blue-500 disabled:bg-gray-700 disabled:text-gray-500">
              Connect Google Account
            </button>
          ) : (
            <button onClick={() => handleSync("meet")} disabled={syncing !== null} className="text-sm px-3 py-1.5 rounded bg-gray-700 text-gray-200 hover:bg-gray-600 disabled:opacity-50">
              {syncing === "meet" ? "Syncing..." : "Sync Transcripts"}
            </button>
          )}
        </div>
```

- [ ] **Step 6: Add Otter.ai card**

Add after the Google Meet card:

```tsx
        {/* Otter.ai */}
        <div className="bg-gray-900 border border-gray-800 rounded-lg p-4">
          <div className="flex items-center justify-between mb-3">
            <h2 className="font-semibold">Otter.ai</h2>
            <span className={`text-xs px-2 py-0.5 rounded ${status.otter.connected ? "bg-green-900 text-green-400" : "bg-gray-800 text-gray-500"}`}>
              {status.otter.connected ? "Connected" : "Not connected"}
            </span>
          </div>
          <p className="text-sm text-gray-400 mb-3">Import meeting transcripts from Otter.ai.</p>
          {!status.otter.connected ? (
            <div className="flex gap-2">
              <input
                type="password"
                value={otterKey}
                onChange={(e) => setOtterKey(e.target.value)}
                placeholder="Otter.ai API key"
                className="flex-1 bg-gray-800 border border-gray-700 rounded px-2 py-1.5 text-sm text-gray-200 placeholder-gray-500 focus:outline-none focus:border-blue-500"
              />
              <button onClick={handleSaveOtterKey} disabled={savingKey || !otterKey.trim()} className="text-sm px-3 py-1.5 rounded bg-blue-600 text-white hover:bg-blue-500 disabled:bg-gray-700 disabled:text-gray-500">
                {savingKey ? "Saving..." : "Save"}
              </button>
            </div>
          ) : (
            <button onClick={() => handleSync("otter")} disabled={syncing !== null} className="text-sm px-3 py-1.5 rounded bg-gray-700 text-gray-200 hover:bg-gray-600 disabled:opacity-50">
              {syncing === "otter" ? "Syncing..." : "Sync Now"}
            </button>
          )}
        </div>
```

- [ ] **Step 7: Build and test**

Run: `cd openraven-ui && bun test tests/ && bun run build`

- [ ] **Step 8: Commit**

```bash
git add openraven-ui/src/pages/ConnectorsPage.tsx
git commit -m "feat(ui): add Google Meet and Otter.ai cards to ConnectorsPage"
```

---

## Task 6: Update .env.example + E2E verification

- [ ] **Step 1: Update .env.example**

Add to `openraven/.env.example` after the Google Connectors section:

```bash
# === Otter.ai (M3) ===
# Get your API key from your Otter.ai account settings.
# Enter it through the Connectors page in the OpenRaven UI.
# The key is stored locally at <working_dir>/otter_api_key.
```

- [ ] **Step 2: Fix Hono proxy to forward request bodies**

Read `openraven-ui/server/index.ts`. The existing `/api/connectors/*` proxy does NOT forward request bodies — it uses `fetch(url, { method: c.req.method })` with no body. This will break `POST /api/connectors/otter/save-key` which expects a JSON body.

Update the proxy route to forward body and content-type:

```typescript
app.all("/api/connectors/*", async (c) => {
  try {
    const url = `${CORE_API_URL}${c.req.path}${c.req.url.includes("?") ? "?" + c.req.url.split("?")[1] : ""}`;
    const headers: Record<string, string> = {};
    const ct = c.req.header("content-type");
    if (ct) headers["content-type"] = ct;
    const body = c.req.method === "GET" || c.req.method === "HEAD" ? undefined : await c.req.text();
    const res = await fetch(url, { method: c.req.method, headers, body });
    const data = await res.json();
    return c.json(data, res.status as any);
  } catch (e) {
    return c.json({ error: `Core engine error: ${(e as Error).message}` }, 502);
  }
});
```

- [ ] **Step 3: Run full test suite**

```bash
cd openraven && .venv/bin/python -m pytest tests/ -v --ignore=tests/test_integration.py --ignore=tests/benchmark/
cd openraven-ui && bun test tests/ && bun run build
```

- [ ] **Step 4: Restart PM2 and verify**

```bash
pm2 restart all && sleep 10
curl -sf http://localhost:8741/api/connectors/status | python3 -m json.tool
```

Expected: Response includes `"meet"` and `"otter"` fields.

- [ ] **Step 5: Commit**

```bash
git add openraven/.env.example
git commit -m "docs: add Otter.ai config to .env.example"
```

---

## Summary

| Task | What | Tests Added |
|---|---|---|
| 1 | Config: otter_key_path + otter_api_key properties | 2 config tests |
| 2 | Google Meet transcript sync in gdrive.py | 2 connector tests |
| 3 | Otter.ai connector module | 5 connector tests |
| 4 | API: Meet sync + Otter save-key/sync endpoints | 4 API tests |
| 5 | ConnectorsPage UI: Meet + Otter cards | Build check |
| 6 | .env.example + E2E verification | Full suite |

**Total new tests: 13**
