# M7.3 E2EE Cloud Sync + M7.8 Chrome Extension — Design Spec

**Date**: 2026-04-05
**Scope**: Server-side encrypted KB sync with user passphrase, and Chrome extension polish for Web Store submission

---

## M7.3: E2EE Cloud Sync

### Goal
Server-side encryption with user passphrase for KB sync between devices. API designed for future browser-side E2EE upgrade.

### Encryption Design

**Flow:**
1. User sets a "sync passphrase" (separate from login password)
2. Server derives encryption key from passphrase using PBKDF2-SHA256 (100K iterations) + random 16-byte salt
3. KB snapshot created (zip of wiki/ + lightrag_data/ + metadata)
4. Snapshot encrypted with AES-256-GCM using derived key + random 12-byte IV
5. Encrypted blob + salt + IV stored at `/data/sync/{tenant_id}/`
6. To restore: user provides passphrase → server derives key → decrypts → restores to tenant dir

**Key management:**
- Salt stored alongside encrypted blob (not secret — needed for key derivation)
- Derived key is ephemeral — exists only during encrypt/decrypt, never persisted
- Passphrase never stored — if forgotten, encrypted data is unrecoverable
- Server stores bcrypt hash of passphrase for verification (user can check they remember it)
- Each snapshot gets its own random salt + IV (no nonce reuse)

### Database Schema

**Table: `sync_config`**

| Column | Type | Notes |
|--------|------|-------|
| `tenant_id` | String(36) PK, FK→tenants | One config per tenant |
| `passphrase_hash` | String(255) | bcrypt hash for verification |
| `last_sync_at` | DateTime(tz) | Nullable |
| `created_at` | DateTime(tz) | Default now() |

**Alembic migration**: 005_sync_config.py (down_revision = "004")

### Module: `openraven/src/openraven/sync/`

**`crypto.py`:**
```python
def derive_key(passphrase: str, salt: bytes) -> bytes:
    """PBKDF2-SHA256, 100K iterations, 32-byte key."""

def encrypt_blob(data: bytes, passphrase: str) -> tuple[bytes, bytes, bytes]:
    """Returns (ciphertext, salt, iv)."""

def decrypt_blob(ciphertext: bytes, passphrase: str, salt: bytes, iv: bytes) -> bytes:
    """Returns plaintext. Raises ValueError on wrong passphrase."""
```

**`snapshots.py`:**
```python
def create_snapshot(data_dir: Path) -> Path:
    """Create a zip snapshot of wiki/ + lightrag_data/. Returns zip path."""

def restore_snapshot(zip_path: Path, data_dir: Path) -> None:
    """Extract snapshot zip to data_dir, overwriting existing data."""

def list_snapshots(sync_dir: Path) -> list[dict]:
    """List stored encrypted snapshots with metadata."""
```

**`routes.py`:**
```python
def create_sync_router(engine, sync_root, data_root) -> APIRouter:
```

### API Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | /api/sync/setup | Auth required | Set sync passphrase (body: `{passphrase}`) |
| POST | /api/sync/upload | Auth required | Create encrypted snapshot (body: `{passphrase}`) |
| POST | /api/sync/download | Auth required | Decrypt and return snapshot (body: `{passphrase}`) |
| GET | /api/sync/status | Auth required | Last sync time, snapshot count, total size |
| DELETE | /api/sync/snapshots/{id} | Auth required | Delete a specific snapshot |

**POST /api/sync/setup:**
- Hashes passphrase with bcrypt, stores in `sync_config`
- Returns `{configured: true}`
- Can be called again to change passphrase (old snapshots become unreadable)

**POST /api/sync/upload:**
- Verifies passphrase against stored hash
- Creates snapshot zip of tenant KB data
- Encrypts with AES-256-GCM
- Stores as `{sync_dir}/{tenant_id}/{timestamp}.enc` with `.meta` sidecar (salt, iv, size, created_at)
- Returns `{snapshot_id, size, created_at}`

**POST /api/sync/download:**
- Verifies passphrase
- Decrypts latest (or specified) snapshot
- Returns zip file as download
- Body: `{passphrase, snapshot_id?}` (latest if omitted)

### Storage Layout

```
/data/sync/{tenant_id}/
├── 2026-04-05T120000.enc        # encrypted blob
├── 2026-04-05T120000.meta       # JSON: {salt_hex, iv_hex, size, created_at}
├── 2026-04-05T150000.enc
└── 2026-04-05T150000.meta
```

### UI: Sync Tab in Settings Page

Third tab alongside Team and Account:
- **Setup section**: Set/change sync passphrase (password input + confirm)
- **Sync Now button**: Creates encrypted snapshot and uploads
- **Snapshots list**: Timestamp, size, delete button
- **Restore button**: Select snapshot → enter passphrase → download or restore in-place
- **Status**: Last sync time, total encrypted storage used

### Security Notes

- Passphrase is transmitted over HTTPS but the server sees it momentarily during key derivation — documented as known limitation, future upgrade to Web Crypto API eliminates this
- Each snapshot has unique salt + IV — no nonce reuse even with same passphrase
- Wrong passphrase produces `InvalidTag` from GCM — caught and returned as 403
- Sync data completely independent from KB data — deleting sync doesn't affect live KB

---

## M7.8: Chrome Extension Polish

### Goal
Polish existing Chrome extension for Web Store submission with options page, context menu, cookie-based auth, and proper branding.

### Options Page (`options.html` + `options.ts`)
- **API URL field**: Default `http://localhost:3002`, configurable for cloud deployment
- **Auth mode selector**: "Local (no auth)" | "Cloud (cookie auth)"
- **Cloud mode**: "Login" button opens OpenRaven login page in new tab. Extension reads `session_id` cookie from configured domain via `chrome.cookies.get()`
- **Test connection** button with green/red status indicator
- Settings persisted to `chrome.storage.sync` (syncs across Chrome instances)

### Context Menu
- Right-click on page → "Save page to OpenRaven"
- Right-click on selected text → "Save selection to OpenRaven"
- Selection mode: wraps selected text in markdown with source URL attribution
- Registered in `background.ts` via `chrome.contextMenus.create()`

### Auth Cookie Support
- `api.ts` reads `session_id` cookie from configured API domain using `chrome.cookies.get()`
- Cookie forwarded in all API requests as `Cookie: session_id=...` header
- Popup shows auth status: "Connected" (green) / "Not logged in" (amber warning with login link)
- Falls back to no-auth mode for localhost connections

### Keyboard Shortcut
- `Ctrl+Shift+S` (Mac: `Cmd+Shift+S`) to save current page
- Registered via `manifest.json` `commands` section
- Handled in `background.ts` via `chrome.commands.onCommand`

### Manifest Changes
```json
{
  "permissions": ["activeTab", "scripting", "cookies", "contextMenus", "storage"],
  "host_permissions": ["<all_urls>"],
  "options_page": "options.html",
  "commands": {
    "save-page": {
      "suggested_key": {"default": "Ctrl+Shift+S", "mac": "Command+Shift+S"},
      "description": "Save current page to OpenRaven"
    }
  }
}
```

### Files

| File | Action | Responsibility |
|------|--------|---------------|
| `openraven-chrome/manifest.json` | Modify | Add permissions, options_page, commands |
| `openraven-chrome/src/options.html` | Create | Settings page HTML |
| `openraven-chrome/src/options.ts` | Create | Settings logic (save/load/test) |
| `openraven-chrome/src/api.ts` | Modify | Configurable URL, cookie auth, settings |
| `openraven-chrome/src/popup.ts` | Modify | Read settings, show auth status |
| `openraven-chrome/src/popup.html` | Modify | Add auth status indicator |
| `openraven-chrome/src/background.ts` | Modify | Context menu, keyboard shortcut, settings |
| `openraven-chrome/src/content.ts` | Modify | Support text selection extraction |
| `openraven-chrome/PRIVACY.md` | Create | Web Store privacy policy |
| `openraven-chrome/tests/` | Modify | Update tests for new functionality |

### Privacy Policy (PRIVACY.md)

For Chrome Web Store submission:
- Extension sends page content only to the user's configured OpenRaven server
- No data is sent to third parties
- No analytics or tracking
- Cookie access is only used for authentication with the user's own server
- All settings stored locally via chrome.storage.sync

---

## Testing Strategy

### M7.3 Tests (`test_sync.py`)
- `encrypt_blob` + `decrypt_blob` round-trip
- Wrong passphrase raises ValueError
- `create_snapshot` produces valid zip
- `restore_snapshot` overwrites data_dir correctly
- API: POST /sync/setup stores passphrase hash
- API: POST /sync/upload creates encrypted file
- API: POST /sync/download decrypts correctly
- API: wrong passphrase returns 403
- API: GET /sync/status returns correct counts

### M7.8 Tests
- `api.ts` uses configured URL (not hardcoded)
- Context menu registration in background.ts
- Content script selection extraction
- Build produces valid extension structure

---

## Out of Scope

- Browser-side Web Crypto API encryption (future upgrade — API already supports pre-encrypted blobs)
- Automatic scheduled sync (manual sync only for MVP)
- Sync conflict resolution beyond last-write-wins
- Snapshot diffing/incremental sync (full snapshots only)
- Chrome extension: page history, KB search from popup, badge counter
- Chrome extension: Firefox/Safari/Edge ports
