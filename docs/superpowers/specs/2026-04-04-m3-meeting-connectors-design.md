# M3 Meeting Connectors — Design Spec

**Goal:** Add Google Meet transcript and Otter.ai meeting note connectors to complete the M3 PRD requirement for "會議記錄連接" (meeting recording connectors).

**Scope:** Two connectors — Google Meet (via existing Drive API) and Otter.ai (via REST API with user-provided API key). No new OAuth flows needed for Meet; Otter.ai uses API key auth managed through the UI.

---

## 1. Google Meet Transcripts (via Drive API)

Google Meet automatically saves transcripts as Google Docs in the user's Drive. These appear with titles matching `"Meeting transcript - *"` or in the "Meet Recordings" folder.

### Implementation

Extend `gdrive.py` with `sync_meet_transcripts()`:

```python
async def sync_meet_transcripts(
    credentials,
    output_dir: Path,
    max_files: int = 50,
) -> list[Path]:
```

This function:
- Queries Drive API for files matching `name contains 'Meeting transcript'` with mimeType `application/vnd.google-apps.document`
- Exports each as plain text (Google Docs export)
- Writes to `output_dir / meet/` subdirectory
- Returns file paths for `pipeline.add_files()`

### API

- `POST /api/connectors/meet/sync` — triggers Meet transcript sync, returns `{files_synced, entities_extracted, articles_generated, errors}`
- Reuses Google OAuth credentials — no separate auth needed
- `GET /api/connectors/status` response updated to include `"meet": {"connected": <bool>}` (same connected state as Drive/Gmail — shares Google token)

### UI

ConnectorsPage gets a "Google Meet" card:
- Shows connected/not connected (mirrors Google Drive status since they share OAuth)
- "Connect Google Account" button if not connected (same handler as Drive/Gmail)
- "Sync Transcripts" button if connected
- Sync result display

---

## 2. Otter.ai Connector

New standalone connector for Otter.ai meeting transcripts via their REST API.

### Auth

- Users provide their Otter.ai API key through the UI
- Key stored at `config.working_dir / "otter_api_key"` as plain text with 0o600 permissions
- New config field: `otter_api_key` (read from file, not env var)
- New config property: `otter_key_path -> Path`

### Implementation

New `otter.py` module:

```python
def transcript_to_markdown(title: str, speakers: list, date: str) -> str:
    """Convert Otter transcript to markdown with speaker labels."""

async def sync_otter(
    api_key: str,
    output_dir: Path,
    max_transcripts: int = 50,
) -> list[Path]:
    """Fetch recent transcripts from Otter.ai API."""
```

The sync function:
- Calls Otter.ai REST API to list recent transcripts
- For each transcript, fetches full content including speaker identification
- Converts to markdown format with speaker labels and timestamps
- Writes to `output_dir / otter/` subdirectory
- Returns file paths for `pipeline.add_files()`

### API

- `POST /api/connectors/otter/save-key` — accepts `{api_key: str}`, saves to disk with 0o600 permissions
- `POST /api/connectors/otter/sync` — triggers Otter sync, returns standard sync result
- `GET /api/connectors/status` response updated to include `"otter": {"connected": <bool>}` (true if API key file exists)

### UI

ConnectorsPage gets an "Otter.ai" card:
- If not connected: API key input field + "Save Key" button
- If connected: "Connected" badge + "Sync Now" button
- Sync result display

---

## 3. ConnectorsPage Layout

The existing 2-card grid becomes a 2x2 grid:

```
┌──────────────────┐  ┌──────────────────┐
│   Google Drive    │  │      Gmail       │
│   [Connected]     │  │   [Connected]    │
│   [Sync Now]      │  │   [Sync Now]     │
└──────────────────┘  └──────────────────┘
┌──────────────────┐  ┌──────────────────┐
│   Google Meet    │  │    Otter.ai      │
│   [Connected]     │  │  [Enter API Key] │
│   [Sync Transcripts]│ │   [Save Key]     │
└──────────────────┘  └──────────────────┘
```

---

## 4. File Structure

| File | Action | Responsibility |
|---|---|---|
| `openraven/src/openraven/connectors/gdrive.py` | Modify | Add `sync_meet_transcripts()` |
| `openraven/src/openraven/connectors/otter.py` | Create | Otter.ai API client, `transcript_to_markdown()`, `sync_otter()`, key save/load |
| `openraven/src/openraven/config.py` | Modify | Add `otter_api_key` field, `otter_key_path` property |
| `openraven/src/openraven/api/server.py` | Modify | Add `POST /meet/sync`, `POST /otter/save-key`, `POST /otter/sync`, update status endpoint |
| `openraven/tests/test_connectors.py` | Modify | Add Meet transcript filter test, Otter markdown test, Otter sync-without-key test |
| `openraven/tests/test_api.py` | Modify | Add Meet sync auth test, Otter save-key test, Otter sync-without-key test |
| `openraven-ui/src/pages/ConnectorsPage.tsx` | Modify | Add Google Meet + Otter.ai cards |
| `openraven/.env.example` | Modify | Document Otter.ai setup |

---

## 5. Tests

### Connector unit tests (test_connectors.py)

- `test_meet_transcript_query_filter()` — verifies the Drive API query string targets Meet transcripts
- `test_meet_sync_requires_credentials()` — returns empty list when credentials=None
- `test_otter_transcript_to_markdown()` — converts transcript data to expected markdown format
- `test_otter_sync_requires_api_key()` — returns empty list when api_key is empty
- `test_otter_key_save_load()` — saves key with 0o600 permissions, loads correctly

### API endpoint tests (test_api.py)

- `test_meet_sync_requires_auth()` — POST /api/connectors/meet/sync returns 401 without Google auth
- `test_otter_save_key_endpoint()` — POST /api/connectors/otter/save-key accepts key
- `test_otter_sync_requires_key()` — POST /api/connectors/otter/sync returns 401 without key
- `test_connectors_status_includes_meet_and_otter()` — status response has meet and otter fields

**Total new tests: 9**

---

## 6. Dependencies

- Google Meet: No new dependencies (reuses google-api-python-client)
- Otter.ai: Uses `httpx` (already available — used by google_auth.py's `exchange_code()`)
