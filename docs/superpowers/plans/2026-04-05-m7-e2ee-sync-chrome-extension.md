# M7.3 E2EE Cloud Sync + M7.8 Chrome Extension Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add server-side encrypted KB sync with user passphrase, and polish the Chrome extension for Web Store submission with options page, context menu, and auth support.

**Architecture:** M7.3 adds a `sync/` module with AES-256-GCM encryption (cryptography lib), snapshot creation/restoration, and FastAPI routes. Storage is local filesystem. M7.8 upgrades the existing Chrome extension with configurable API URL, cookie auth, context menus, and keyboard shortcut.

**Tech Stack:** Python 3.12 + cryptography (sync), TypeScript + Chrome Extensions MV3 (extension), Bun (build)

---

## File Structure

### M7.3 E2EE Sync
| File | Action | Responsibility |
|------|--------|---------------|
| `openraven/pyproject.toml` | Modify | Add `cryptography` dependency |
| `openraven/src/openraven/auth/db.py` | Modify | Add `sync_config` table |
| `openraven/alembic/versions/005_sync_config.py` | Create | Migration |
| `openraven/src/openraven/sync/__init__.py` | Create | Package marker |
| `openraven/src/openraven/sync/crypto.py` | Create | encrypt_blob, decrypt_blob, derive_key |
| `openraven/src/openraven/sync/snapshots.py` | Create | create_snapshot, restore_snapshot, list_snapshots |
| `openraven/src/openraven/sync/routes.py` | Create | /api/sync/* endpoints |
| `openraven/src/openraven/api/server.py` | Modify | Register sync router |
| `openraven/tests/test_sync.py` | Create | Crypto + snapshot + API tests |
| `openraven-ui/src/pages/SettingsPage.tsx` | Modify | Add Sync tab |
| `openraven-ui/server/index.ts` | Modify | Add /api/sync proxy |

### M7.8 Chrome Extension
| File | Action | Responsibility |
|------|--------|---------------|
| `openraven-chrome/manifest.json` | Modify | Permissions, options, commands |
| `openraven-chrome/src/options.html` | Create | Settings page |
| `openraven-chrome/src/options.ts` | Create | Settings logic |
| `openraven-chrome/src/api.ts` | Modify | Configurable URL, cookie auth |
| `openraven-chrome/src/popup.ts` | Modify | Read settings, auth status |
| `openraven-chrome/src/popup.html` | Modify | Auth status indicator |
| `openraven-chrome/src/background.ts` | Modify | Context menu, keyboard shortcut |
| `openraven-chrome/src/content.ts` | Modify | Selection extraction |
| `openraven-chrome/package.json` | Modify | Build options page |
| `openraven-chrome/PRIVACY.md` | Create | Web Store privacy policy |

---

## Part 1: M7.3 E2EE Cloud Sync

### Task 1: Add cryptography Dependency + Sync DB Schema

**Files:**
- Modify: `openraven/pyproject.toml`
- Modify: `openraven/src/openraven/auth/db.py`
- Create: `openraven/alembic/versions/005_sync_config.py`

- [ ] **Step 1: Add cryptography to pyproject.toml**

In `openraven/pyproject.toml`, add `"cryptography>=43.0.0"` to the `dependencies` list (after `"neo4j>=5.0.0"`).

- [ ] **Step 2: Add sync_config table to db.py**

In `openraven/src/openraven/auth/db.py`, add after the `invitations` table and before `get_engine`:

```python
sync_config = Table(
    "sync_config", metadata,
    Column("tenant_id", String(36), ForeignKey("tenants.id", ondelete="CASCADE"), primary_key=True),
    Column("passphrase_hash", String(255), nullable=False),
    Column("last_sync_at", DateTime(timezone=True), nullable=True),
    Column("created_at", DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)),
)
```

- [ ] **Step 3: Create Alembic migration**

Create `openraven/alembic/versions/005_sync_config.py`:

```python
"""Sync config table for E2EE cloud sync.

Revision ID: 005
Create Date: 2026-04-05
"""
from alembic import op
import sqlalchemy as sa

revision = "005"
down_revision = "004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "sync_config",
        sa.Column("tenant_id", sa.String(36), sa.ForeignKey("tenants.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("passphrase_hash", sa.String(255), nullable=False),
        sa.Column("last_sync_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("sync_config")
```

- [ ] **Step 4: Verify**

```bash
cd /home/ubuntu/source/OpenRaven/openraven && python3 -c "
from openraven.auth.db import get_engine, create_tables
from sqlalchemy import inspect
engine = get_engine('sqlite:///test_sync.db')
create_tables(engine)
tables = inspect(engine).get_table_names()
assert 'sync_config' in tables, f'sync_config not found in {tables}'
print(f'OK: {tables}')
import os; os.remove('test_sync.db')
"
```

- [ ] **Step 5: Commit**

```bash
cd /home/ubuntu/source/OpenRaven && git add openraven/pyproject.toml openraven/src/openraven/auth/db.py openraven/alembic/versions/005_sync_config.py && git commit -m "$(cat <<'EOF'
feat(m7): add cryptography dep and sync_config table

New sync_config table (tenant_id PK, passphrase_hash, last_sync_at)
for E2EE cloud sync. Alembic migration 005.

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 2: Crypto Module

**Files:**
- Create: `openraven/src/openraven/sync/__init__.py`
- Create: `openraven/src/openraven/sync/crypto.py`
- Create: `openraven/tests/test_sync.py`

- [ ] **Step 1: Write failing tests**

Create `openraven/tests/test_sync.py`:

```python
import pytest


def test_derive_key_deterministic():
    from openraven.sync.crypto import derive_key
    salt = b"\x00" * 16
    key1 = derive_key("mypassphrase", salt)
    key2 = derive_key("mypassphrase", salt)
    assert key1 == key2
    assert len(key1) == 32  # 256 bits


def test_derive_key_different_salt():
    from openraven.sync.crypto import derive_key
    key1 = derive_key("mypassphrase", b"\x00" * 16)
    key2 = derive_key("mypassphrase", b"\x01" * 16)
    assert key1 != key2


def test_encrypt_decrypt_roundtrip():
    from openraven.sync.crypto import encrypt_blob, decrypt_blob
    plaintext = b"Hello, this is secret knowledge base data!" * 100
    ciphertext, salt, iv = encrypt_blob(plaintext, "mypassphrase")
    assert ciphertext != plaintext
    assert len(salt) == 16
    assert len(iv) == 12
    result = decrypt_blob(ciphertext, "mypassphrase", salt, iv)
    assert result == plaintext


def test_decrypt_wrong_passphrase():
    from openraven.sync.crypto import encrypt_blob, decrypt_blob
    plaintext = b"Secret data"
    ciphertext, salt, iv = encrypt_blob(plaintext, "correct")
    with pytest.raises(ValueError, match="passphrase"):
        decrypt_blob(ciphertext, "wrong", salt, iv)


def test_encrypt_produces_different_output_each_time():
    from openraven.sync.crypto import encrypt_blob
    plaintext = b"Same data"
    ct1, salt1, iv1 = encrypt_blob(plaintext, "pass")
    ct2, salt2, iv2 = encrypt_blob(plaintext, "pass")
    # Different salt + IV each time → different ciphertext
    assert salt1 != salt2 or iv1 != iv2
    assert ct1 != ct2
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /home/ubuntu/source/OpenRaven/openraven && python3 -m pytest tests/test_sync.py -v 2>&1 | tail -10
```

- [ ] **Step 3: Implement crypto.py**

Create `openraven/src/openraven/sync/__init__.py` (empty file).

Create `openraven/src/openraven/sync/crypto.py`:

```python
"""AES-256-GCM encryption for E2EE cloud sync."""
from __future__ import annotations

import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes


def derive_key(passphrase: str, salt: bytes) -> bytes:
    """Derive a 256-bit key from passphrase using PBKDF2-SHA256."""
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100_000,
    )
    return kdf.derive(passphrase.encode("utf-8"))


def encrypt_blob(data: bytes, passphrase: str) -> tuple[bytes, bytes, bytes]:
    """Encrypt data with AES-256-GCM. Returns (ciphertext, salt, iv)."""
    salt = os.urandom(16)
    iv = os.urandom(12)
    key = derive_key(passphrase, salt)
    aesgcm = AESGCM(key)
    ciphertext = aesgcm.encrypt(iv, data, None)
    return ciphertext, salt, iv


def decrypt_blob(ciphertext: bytes, passphrase: str, salt: bytes, iv: bytes) -> bytes:
    """Decrypt data with AES-256-GCM. Raises ValueError on wrong passphrase."""
    key = derive_key(passphrase, salt)
    aesgcm = AESGCM(key)
    try:
        return aesgcm.decrypt(iv, ciphertext, None)
    except Exception:
        raise ValueError("Decryption failed — wrong passphrase or corrupted data")
```

- [ ] **Step 4: Run tests**

```bash
cd /home/ubuntu/source/OpenRaven/openraven && python3 -m pytest tests/test_sync.py -v 2>&1 | tail -10
```
Expected: All 5 tests PASS.

- [ ] **Step 5: Commit**

```bash
cd /home/ubuntu/source/OpenRaven && git add openraven/src/openraven/sync/ openraven/tests/test_sync.py && git commit -m "$(cat <<'EOF'
feat(m7): add AES-256-GCM crypto module for E2EE sync

derive_key (PBKDF2-SHA256, 100K iterations), encrypt_blob, decrypt_blob.
Random salt + IV per encryption. 5 tests.

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 3: Snapshots Module

**Files:**
- Create: `openraven/src/openraven/sync/snapshots.py`
- Modify: `openraven/tests/test_sync.py`

- [ ] **Step 1: Add snapshot tests**

Append to `openraven/tests/test_sync.py`:

```python
import json
import zipfile
from pathlib import Path


def test_create_snapshot(tmp_path):
    from openraven.sync.snapshots import create_snapshot
    # Set up fake KB data
    data_dir = tmp_path / "kb"
    wiki_dir = data_dir / "wiki"
    wiki_dir.mkdir(parents=True)
    (wiki_dir / "article.md").write_text("# Test Article")
    lightrag_dir = data_dir / "lightrag_data"
    lightrag_dir.mkdir()
    (lightrag_dir / "graph_chunk_entity_relation.graphml").write_text("<graphml/>")

    zip_path = create_snapshot(data_dir, tmp_path / "out")
    assert zip_path.exists()
    assert zip_path.suffix == ".zip"
    with zipfile.ZipFile(zip_path) as zf:
        names = zf.namelist()
        assert "wiki/article.md" in names
        assert "lightrag_data/graph_chunk_entity_relation.graphml" in names
        assert "snapshot_meta.json" in names


def test_create_snapshot_empty_dir(tmp_path):
    from openraven.sync.snapshots import create_snapshot
    data_dir = tmp_path / "empty_kb"
    data_dir.mkdir()
    zip_path = create_snapshot(data_dir, tmp_path / "out")
    assert zip_path.exists()


def test_restore_snapshot(tmp_path):
    from openraven.sync.snapshots import create_snapshot, restore_snapshot
    # Create source
    src = tmp_path / "src"
    wiki_dir = src / "wiki"
    wiki_dir.mkdir(parents=True)
    (wiki_dir / "article.md").write_text("# Original")
    zip_path = create_snapshot(src, tmp_path / "snap")

    # Restore to different dir
    dest = tmp_path / "dest"
    dest.mkdir()
    restore_snapshot(zip_path, dest)
    assert (dest / "wiki" / "article.md").read_text() == "# Original"


def test_list_snapshots(tmp_path):
    from openraven.sync.snapshots import list_snapshots
    sync_dir = tmp_path / "sync"
    sync_dir.mkdir()
    # Create fake snapshot files
    (sync_dir / "2026-04-05T120000.enc").write_bytes(b"encrypted")
    (sync_dir / "2026-04-05T120000.meta").write_text(json.dumps({
        "salt_hex": "aa" * 16, "iv_hex": "bb" * 12,
        "size": 1024, "created_at": "2026-04-05T12:00:00",
    }))
    (sync_dir / "2026-04-05T150000.enc").write_bytes(b"encrypted2")
    (sync_dir / "2026-04-05T150000.meta").write_text(json.dumps({
        "salt_hex": "cc" * 16, "iv_hex": "dd" * 12,
        "size": 2048, "created_at": "2026-04-05T15:00:00",
    }))

    result = list_snapshots(sync_dir)
    assert len(result) == 2
    assert result[0]["size"] == 2048  # newest first
```

- [ ] **Step 2: Implement snapshots.py**

Create `openraven/src/openraven/sync/snapshots.py`:

```python
"""KB snapshot creation, restoration, and listing."""
from __future__ import annotations

import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path


def create_snapshot(data_dir: Path, output_dir: Path) -> Path:
    """Create a zip snapshot of KB data. Returns zip path."""
    output_dir.mkdir(parents=True, exist_ok=True)
    zip_path = output_dir / "snapshot.zip"

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        # Wiki articles
        wiki_dir = data_dir / "wiki"
        if wiki_dir.exists():
            for f in sorted(wiki_dir.rglob("*")):
                if f.is_file():
                    zf.write(f, f"wiki/{f.relative_to(wiki_dir)}")

        # LightRAG data
        lightrag_dir = data_dir / "lightrag_data"
        if lightrag_dir.exists():
            for f in sorted(lightrag_dir.rglob("*")):
                if f.is_file():
                    zf.write(f, f"lightrag_data/{f.relative_to(lightrag_dir)}")

        # Metadata
        meta = {
            "created_at": datetime.now(timezone.utc).isoformat(),
            "source_dir": str(data_dir),
        }
        zf.writestr("snapshot_meta.json", json.dumps(meta, indent=2))

    return zip_path


def restore_snapshot(zip_path: Path, data_dir: Path) -> None:
    """Extract a snapshot zip to data_dir."""
    data_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(data_dir)


def list_snapshots(sync_dir: Path) -> list[dict]:
    """List encrypted snapshots in sync dir, newest first."""
    snapshots = []
    if not sync_dir.exists():
        return snapshots

    for meta_file in sorted(sync_dir.glob("*.meta"), reverse=True):
        enc_file = meta_file.with_suffix(".enc")
        if not enc_file.exists():
            continue
        try:
            meta = json.loads(meta_file.read_text(encoding="utf-8"))
            snapshots.append({
                "id": meta_file.stem,
                "size": meta.get("size", 0),
                "created_at": meta.get("created_at"),
                "salt_hex": meta.get("salt_hex"),
                "iv_hex": meta.get("iv_hex"),
            })
        except (json.JSONDecodeError, OSError):
            continue

    return snapshots
```

- [ ] **Step 3: Run tests**

```bash
cd /home/ubuntu/source/OpenRaven/openraven && python3 -m pytest tests/test_sync.py -v 2>&1 | tail -15
```
Expected: All 9 tests PASS.

- [ ] **Step 4: Commit**

```bash
cd /home/ubuntu/source/OpenRaven && git add openraven/src/openraven/sync/snapshots.py openraven/tests/test_sync.py && git commit -m "$(cat <<'EOF'
feat(m7): add KB snapshot create, restore, and list functions

create_snapshot zips wiki + lightrag_data. restore_snapshot extracts.
list_snapshots reads .enc/.meta pairs from sync directory.

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 4: Sync API Routes

**Files:**
- Create: `openraven/src/openraven/sync/routes.py`
- Modify: `openraven/tests/test_sync.py`

- [ ] **Step 1: Add API tests**

Append to `openraven/tests/test_sync.py`:

```python
import uuid
from datetime import datetime, timezone as tz

from sqlalchemy import insert
from fastapi.testclient import TestClient

from openraven.auth.db import create_tables, get_engine, users, tenants, tenant_members


@pytest.fixture
def sync_engine(tmp_path):
    engine = get_engine(f"sqlite:///{tmp_path}/test_sync_api.db")
    create_tables(engine)
    return engine


@pytest.fixture
def sync_owner(sync_engine, tmp_path):
    user_id = str(uuid.uuid4())
    tenant_id = str(uuid.uuid4())
    now = datetime.now(tz.utc)
    with sync_engine.connect() as conn:
        conn.execute(insert(users).values(
            id=user_id, email="sync@test.com", name="Sync User",
            password_hash="$2b$12$fake", created_at=now, updated_at=now,
        ))
        conn.execute(insert(tenants).values(
            id=tenant_id, name="Sync Tenant", owner_user_id=user_id, created_at=now,
        ))
        conn.execute(insert(tenant_members).values(
            tenant_id=tenant_id, user_id=user_id, role="owner",
        ))
        conn.commit()
    # Create KB data
    data_dir = tmp_path / "tenants" / tenant_id
    wiki_dir = data_dir / "wiki"
    wiki_dir.mkdir(parents=True)
    (wiki_dir / "test.md").write_text("# Sync Test")
    return user_id, tenant_id


@pytest.fixture
def app_with_sync(sync_engine, sync_owner, tmp_path):
    from openraven.sync.routes import create_sync_router
    from openraven.auth.models import AuthContext
    from fastapi import FastAPI, Request
    from starlette.middleware.base import BaseHTTPMiddleware

    user_id, tenant_id = sync_owner
    app = FastAPI()

    class MockAuth(BaseHTTPMiddleware):
        async def dispatch(self, request, call_next):
            request.state.auth = AuthContext(user_id=user_id, tenant_id=tenant_id, email="sync@test.com")
            return await call_next(request)

    app.add_middleware(MockAuth)
    app.include_router(create_sync_router(
        sync_engine,
        sync_root=tmp_path / "sync_data",
        data_root=tmp_path / "tenants",
    ), prefix="/api/sync")
    return app


def test_api_sync_setup(app_with_sync):
    client = TestClient(app_with_sync)
    res = client.post("/api/sync/setup", json={"passphrase": "mysyncpass123"})
    assert res.status_code == 200
    assert res.json()["configured"] is True


def test_api_sync_upload(app_with_sync):
    client = TestClient(app_with_sync)
    client.post("/api/sync/setup", json={"passphrase": "mysyncpass123"})
    res = client.post("/api/sync/upload", json={"passphrase": "mysyncpass123"})
    assert res.status_code == 200
    data = res.json()
    assert "snapshot_id" in data
    assert data["size"] > 0


def test_api_sync_upload_wrong_passphrase(app_with_sync):
    client = TestClient(app_with_sync)
    client.post("/api/sync/setup", json={"passphrase": "mysyncpass123"})
    res = client.post("/api/sync/upload", json={"passphrase": "wrong"})
    assert res.status_code == 403


def test_api_sync_download(app_with_sync):
    client = TestClient(app_with_sync)
    client.post("/api/sync/setup", json={"passphrase": "mysyncpass123"})
    client.post("/api/sync/upload", json={"passphrase": "mysyncpass123"})
    res = client.post("/api/sync/download", json={"passphrase": "mysyncpass123"})
    assert res.status_code == 200
    assert "application/zip" in res.headers.get("content-type", "")


def test_api_sync_status(app_with_sync):
    client = TestClient(app_with_sync)
    res = client.get("/api/sync/status")
    assert res.status_code == 200
    data = res.json()
    assert data["configured"] is False
    assert data["snapshot_count"] == 0
```

- [ ] **Step 2: Implement routes.py**

Create `openraven/src/openraven/sync/routes.py`:

```python
"""Sync API routes for E2EE cloud sync."""
from __future__ import annotations

import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Request, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy import select, delete
from sqlalchemy.engine import Engine

from openraven.auth.db import sync_config
from openraven.auth.passwords import hash_password, verify_password
from openraven.sync.crypto import encrypt_blob, decrypt_blob
from openraven.sync.snapshots import create_snapshot, list_snapshots


class PassphraseRequest(BaseModel):
    passphrase: str


class DownloadRequest(BaseModel):
    passphrase: str
    snapshot_id: str | None = None


def create_sync_router(
    engine: Engine,
    sync_root: Path = Path("/data/sync"),
    data_root: Path = Path("/data/tenants"),
) -> APIRouter:
    router = APIRouter()

    def _get_auth(request: Request):
        auth = getattr(request.state, "auth", None)
        if not auth:
            raise HTTPException(401, "Not authenticated")
        return auth

    def _verify_passphrase(tenant_id: str, passphrase: str) -> None:
        with engine.connect() as conn:
            row = conn.execute(
                select(sync_config.c.passphrase_hash)
                .where(sync_config.c.tenant_id == tenant_id)
            ).first()
        if not row:
            raise HTTPException(400, "Sync not configured — set a passphrase first")
        if not verify_password(passphrase, row.passphrase_hash):
            raise HTTPException(403, "Incorrect sync passphrase")

    @router.post("/setup")
    async def setup_sync(request: Request, body: PassphraseRequest):
        auth = _get_auth(request)
        pw_hash = hash_password(body.passphrase)
        from sqlalchemy import insert as sa_insert, update as sa_update
        with engine.connect() as conn:
            existing = conn.execute(
                select(sync_config).where(sync_config.c.tenant_id == auth.tenant_id)
            ).first()
            if existing:
                conn.execute(
                    sa_update(sync_config)
                    .where(sync_config.c.tenant_id == auth.tenant_id)
                    .values(passphrase_hash=pw_hash)
                )
            else:
                conn.execute(sa_insert(sync_config).values(
                    tenant_id=auth.tenant_id,
                    passphrase_hash=pw_hash,
                ))
            conn.commit()
        return {"configured": True}

    @router.post("/upload")
    async def upload_snapshot(request: Request, body: PassphraseRequest):
        auth = _get_auth(request)
        _verify_passphrase(auth.tenant_id, body.passphrase)

        data_dir = data_root / auth.tenant_id
        if not data_dir.exists():
            raise HTTPException(404, "No knowledge base data found")

        # Create snapshot
        snap_dir = Path(tempfile.mkdtemp())
        zip_path = create_snapshot(data_dir, snap_dir)
        plaintext = zip_path.read_bytes()

        # Encrypt
        ciphertext, salt, iv = encrypt_blob(plaintext, body.passphrase)

        # Store
        sync_dir = sync_root / auth.tenant_id
        sync_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H%M%S")
        enc_path = sync_dir / f"{timestamp}.enc"
        meta_path = sync_dir / f"{timestamp}.meta"
        enc_path.write_bytes(ciphertext)
        meta_path.write_text(json.dumps({
            "salt_hex": salt.hex(),
            "iv_hex": iv.hex(),
            "size": len(ciphertext),
            "created_at": datetime.now(timezone.utc).isoformat(),
        }), encoding="utf-8")

        # Update last_sync_at
        from sqlalchemy import update as sa_update
        with engine.connect() as conn:
            conn.execute(
                sa_update(sync_config)
                .where(sync_config.c.tenant_id == auth.tenant_id)
                .values(last_sync_at=datetime.now(timezone.utc))
            )
            conn.commit()

        # Cleanup temp
        import shutil
        shutil.rmtree(snap_dir, ignore_errors=True)

        return {"snapshot_id": timestamp, "size": len(ciphertext), "created_at": datetime.now(timezone.utc).isoformat()}

    @router.post("/download")
    async def download_snapshot(request: Request, body: DownloadRequest, background_tasks: BackgroundTasks):
        auth = _get_auth(request)
        _verify_passphrase(auth.tenant_id, body.passphrase)

        sync_dir = sync_root / auth.tenant_id
        snapshots = list_snapshots(sync_dir)
        if not snapshots:
            raise HTTPException(404, "No snapshots found")

        # Find the requested snapshot (or latest)
        if body.snapshot_id:
            snap = next((s for s in snapshots if s["id"] == body.snapshot_id), None)
            if not snap:
                raise HTTPException(404, "Snapshot not found")
        else:
            snap = snapshots[0]  # newest

        enc_path = sync_dir / f"{snap['id']}.enc"
        ciphertext = enc_path.read_bytes()
        salt = bytes.fromhex(snap["salt_hex"])
        iv = bytes.fromhex(snap["iv_hex"])

        try:
            plaintext = decrypt_blob(ciphertext, body.passphrase, salt, iv)
        except ValueError:
            raise HTTPException(403, "Incorrect passphrase — cannot decrypt snapshot")

        # Write decrypted zip to temp file
        import shutil
        tmp_dir = Path(tempfile.mkdtemp())
        zip_path = tmp_dir / "snapshot.zip"
        zip_path.write_bytes(plaintext)
        background_tasks.add_task(shutil.rmtree, str(tmp_dir))
        return FileResponse(path=str(zip_path), media_type="application/zip", filename="openraven_snapshot.zip")

    @router.get("/status")
    async def sync_status(request: Request):
        auth = _get_auth(request)
        with engine.connect() as conn:
            row = conn.execute(
                select(sync_config).where(sync_config.c.tenant_id == auth.tenant_id)
            ).first()

        sync_dir = sync_root / auth.tenant_id
        snapshots = list_snapshots(sync_dir)
        total_size = sum(s["size"] for s in snapshots)

        return {
            "configured": row is not None,
            "last_sync_at": row.last_sync_at.isoformat() if row and row.last_sync_at else None,
            "snapshot_count": len(snapshots),
            "total_size": total_size,
            "snapshots": snapshots,
        }

    @router.delete("/snapshots/{snapshot_id}")
    async def delete_snapshot(snapshot_id: str, request: Request):
        auth = _get_auth(request)
        sync_dir = sync_root / auth.tenant_id
        enc_path = sync_dir / f"{snapshot_id}.enc"
        meta_path = sync_dir / f"{snapshot_id}.meta"
        if not enc_path.exists():
            raise HTTPException(404, "Snapshot not found")
        enc_path.unlink()
        meta_path.unlink(missing_ok=True)
        return {"deleted": True}

    return router
```

- [ ] **Step 3: Run tests**

```bash
cd /home/ubuntu/source/OpenRaven/openraven && python3 -m pytest tests/test_sync.py -v 2>&1 | tail -20
```
Expected: All 14 tests PASS.

- [ ] **Step 4: Commit**

```bash
cd /home/ubuntu/source/OpenRaven && git add openraven/src/openraven/sync/routes.py openraven/tests/test_sync.py && git commit -m "$(cat <<'EOF'
feat(m7): add sync API routes — setup, upload, download, status, delete

POST /sync/setup (set passphrase), POST /sync/upload (encrypt + store),
POST /sync/download (decrypt + return zip), GET /sync/status,
DELETE /sync/snapshots/{id}. Passphrase verified via bcrypt.

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 5: Register Sync Routes + BFF Proxy + UI Tab

**Files:**
- Modify: `openraven/src/openraven/api/server.py`
- Modify: `openraven-ui/server/index.ts`
- Modify: `openraven-ui/src/pages/SettingsPage.tsx`

- [ ] **Step 1: Register sync router in server.py**

In `openraven/src/openraven/api/server.py`, inside `if config.auth_enabled:` block (after the account router registration), add:

```python
        from openraven.sync.routes import create_sync_router
        app.include_router(create_sync_router(auth_engine), prefix="/api/sync", tags=["sync"])
```

- [ ] **Step 2: Add BFF proxy**

In `openraven-ui/server/index.ts`, after the account proxy blocks, add:

```typescript
// Sync proxy with binary passthrough for snapshot download
app.all("/api/sync/*", async (c) => {
  try {
    if (c.req.path.endsWith("/download")) {
      const url = `${CORE_API_URL}${c.req.path}${c.req.url.includes("?") ? "?" + c.req.url.split("?")[1] : ""}`;
      const body = c.req.method === "POST" ? await c.req.text() : undefined;
      const res = await fetch(url, {
        method: c.req.method,
        headers: { Cookie: c.req.header("Cookie") ?? "", "Content-Type": "application/json" },
        body,
      });
      return new Response(res.body, {
        status: res.status,
        headers: {
          "content-type": res.headers.get("content-type") || "application/zip",
          "content-disposition": res.headers.get("content-disposition") || "attachment; filename=openraven_snapshot.zip",
        },
      });
    }
    return await proxyToCore(c);
  } catch (e) { return c.json({ error: `Core engine error: ${(e as Error).message}` }, 502); }
});
app.all("/api/sync", async (c) => {
  try { return await proxyToCore(c); }
  catch (e) { return c.json({ error: `Core engine error: ${(e as Error).message}` }, 502); }
});
```

- [ ] **Step 3: Add Sync tab to SettingsPage**

In `openraven-ui/src/pages/SettingsPage.tsx`:

Change the tab type from `"team" | "account"` to `"team" | "account" | "sync"` and add `"sync"` to the tabs array.

Then add `{tab === "sync" && <SyncTab />}` after the AccountTab conditional.

Add this `SyncTab` component at the bottom of the file (before the final closing):

```tsx
function SyncTab() {
  const [status, setStatus] = useState<{ configured: boolean; last_sync_at: string | null; snapshot_count: number; total_size: number; snapshots: any[] } | null>(null);
  const [passphrase, setPassphrase] = useState("");
  const [confirm, setConfirm] = useState("");
  const [syncing, setSyncing] = useState(false);
  const [message, setMessage] = useState("");

  useEffect(() => {
    fetch("/api/sync/status").then(r => r.json()).then(setStatus).catch(() => {});
  }, []);

  async function handleSetup() {
    if (passphrase.length < 8) { setMessage("Passphrase must be at least 8 characters"); return; }
    if (passphrase !== confirm) { setMessage("Passphrases do not match"); return; }
    const res = await fetch("/api/sync/setup", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ passphrase }),
    });
    if (res.ok) { setMessage("Sync passphrase configured!"); setPassphrase(""); setConfirm(""); fetch("/api/sync/status").then(r => r.json()).then(setStatus); }
    else { setMessage("Failed to configure"); }
  }

  async function handleSync() {
    const pp = prompt("Enter your sync passphrase:");
    if (!pp) return;
    setSyncing(true); setMessage("");
    const res = await fetch("/api/sync/upload", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ passphrase: pp }),
    });
    if (res.ok) { setMessage("Snapshot uploaded successfully!"); fetch("/api/sync/status").then(r => r.json()).then(setStatus); }
    else { const d = await res.json(); setMessage(d.detail || "Sync failed"); }
    setSyncing(false);
  }

  async function handleDownload(snapshotId?: string) {
    const pp = prompt("Enter your sync passphrase to download:");
    if (!pp) return;
    const res = await fetch("/api/sync/download", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ passphrase: pp, snapshot_id: snapshotId }),
    });
    if (res.ok) {
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a"); a.href = url; a.download = "openraven_snapshot.zip"; a.click();
      URL.revokeObjectURL(url);
    } else { const d = await res.json(); alert(d.detail || "Download failed"); }
  }

  async function handleDelete(id: string) {
    await fetch(`/api/sync/snapshots/${id}`, { method: "DELETE" });
    fetch("/api/sync/status").then(r => r.json()).then(setStatus);
  }

  return (
    <div>
      <h2 className="text-xl mb-4" style={{ color: "var(--color-text)" }}>Cloud Sync (E2EE)</h2>
      {!status?.configured ? (
        <div className="mb-6">
          <p className="text-sm mb-4" style={{ color: "var(--color-text-muted)" }}>Set a sync passphrase to enable encrypted cloud sync. This passphrase encrypts your knowledge base — if you forget it, your synced data cannot be recovered.</p>
          <div className="flex flex-col gap-3 max-w-sm">
            <input type="password" value={passphrase} onChange={e => setPassphrase(e.target.value)} placeholder="Sync passphrase (min 8 chars)" aria-label="Sync passphrase"
              className="px-3 py-2 text-sm" style={{ background: "var(--bg-surface)", border: "1px solid var(--color-border)", color: "var(--color-text)" }} />
            <input type="password" value={confirm} onChange={e => setConfirm(e.target.value)} placeholder="Confirm passphrase" aria-label="Confirm sync passphrase"
              className="px-3 py-2 text-sm" style={{ background: "var(--bg-surface)", border: "1px solid var(--color-border)", color: "var(--color-text)" }} />
            <button onClick={handleSetup} className="px-4 py-2 text-sm cursor-pointer" style={{ background: "var(--color-dark)", color: "var(--color-text-on-brand)" }}>Set Passphrase</button>
          </div>
        </div>
      ) : (
        <div className="mb-6">
          <div className="flex gap-4 mb-4">
            <button onClick={handleSync} disabled={syncing} className="px-4 py-2 text-sm cursor-pointer disabled:opacity-50"
              style={{ background: "var(--color-dark)", color: "var(--color-text-on-brand)" }}>{syncing ? "Syncing..." : "Sync Now"}</button>
            <button onClick={() => handleDownload()} className="px-4 py-2 text-sm cursor-pointer"
              style={{ background: "var(--bg-surface)", border: "1px solid var(--color-border)", color: "var(--color-text)" }}>Download Latest</button>
          </div>
          <div className="grid grid-cols-3 gap-4 mb-6 text-sm">
            <div><div className="text-xs" style={{ color: "var(--color-text-muted)" }}>Last sync</div><div style={{ color: "var(--color-text)" }}>{status.last_sync_at ? new Date(status.last_sync_at).toLocaleString() : "Never"}</div></div>
            <div><div className="text-xs" style={{ color: "var(--color-text-muted)" }}>Snapshots</div><div style={{ color: "var(--color-text)" }}>{status.snapshot_count}</div></div>
            <div><div className="text-xs" style={{ color: "var(--color-text-muted)" }}>Total size</div><div style={{ color: "var(--color-text)" }}>{(status.total_size / 1024 / 1024).toFixed(1)} MB</div></div>
          </div>
          {status.snapshots.length > 0 && (
            <table className="w-full text-sm" style={{ borderCollapse: "collapse" }}>
              <thead><tr style={{ borderBottom: "2px solid var(--color-border)" }}>
                {["Date", "Size", ""].map(h => <th key={h} className="text-left py-2 px-3 text-xs uppercase" style={{ color: "var(--color-text-muted)" }}>{h}</th>)}
              </tr></thead>
              <tbody>{status.snapshots.map(s => (
                <tr key={s.id} style={{ borderBottom: "1px solid var(--color-border)" }}>
                  <td className="py-2 px-3 text-xs" style={{ color: "var(--color-text)" }}>{s.created_at ? new Date(s.created_at).toLocaleString() : s.id}</td>
                  <td className="py-2 px-3 text-xs" style={{ color: "var(--color-text-muted)" }}>{(s.size / 1024).toFixed(0)} KB</td>
                  <td className="py-2 px-3 text-right flex gap-2 justify-end">
                    <button onClick={() => handleDownload(s.id)} className="text-xs cursor-pointer" style={{ color: "var(--color-brand)" }}>Download</button>
                    <button onClick={() => handleDelete(s.id)} className="text-xs cursor-pointer" style={{ color: "var(--color-error, #dc2626)" }}>Delete</button>
                  </td>
                </tr>
              ))}</tbody>
            </table>
          )}
        </div>
      )}
      {message && <p className="text-sm mt-2" style={{ color: "var(--color-brand)" }}>{message}</p>}
    </div>
  );
}
```

- [ ] **Step 4: Verify builds**

```bash
cd /home/ubuntu/source/OpenRaven/openraven-ui && bun run build 2>&1 | tail -5
```

- [ ] **Step 5: Commit**

```bash
cd /home/ubuntu/source/OpenRaven && git add openraven/src/openraven/api/server.py openraven-ui/server/index.ts openraven-ui/src/pages/SettingsPage.tsx && git commit -m "$(cat <<'EOF'
feat(m7): register sync routes, add BFF proxy, and Sync tab in Settings

/api/sync/* routes active when DATABASE_URL set. BFF proxy with
binary passthrough for snapshot download. Settings page gets third
tab for sync setup, upload, download, and snapshot management.

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Part 2: M7.8 Chrome Extension Polish

### Task 6: Options Page + Configurable API

**Files:**
- Modify: `openraven-chrome/manifest.json`
- Create: `openraven-chrome/src/options.html`
- Create: `openraven-chrome/src/options.ts`
- Modify: `openraven-chrome/src/api.ts`
- Modify: `openraven-chrome/package.json`

- [ ] **Step 1: Update manifest.json**

Replace `openraven-chrome/manifest.json`:

```json
{
  "manifest_version": 3,
  "name": "OpenRaven",
  "version": "0.2.0",
  "description": "Save web pages to your personal AI knowledge base",
  "permissions": ["activeTab", "scripting", "cookies", "contextMenus", "storage"],
  "host_permissions": ["<all_urls>"],
  "action": {
    "default_popup": "popup.html",
    "default_icon": {
      "16": "icons/icon-16.png",
      "48": "icons/icon-48.png",
      "128": "icons/icon-128.png"
    }
  },
  "background": {
    "service_worker": "background.js",
    "type": "module"
  },
  "options_page": "options.html",
  "commands": {
    "save-page": {
      "suggested_key": { "default": "Ctrl+Shift+S", "mac": "Command+Shift+S" },
      "description": "Save current page to OpenRaven"
    }
  },
  "icons": {
    "16": "icons/icon-16.png",
    "48": "icons/icon-48.png",
    "128": "icons/icon-128.png"
  }
}
```

- [ ] **Step 2: Create options.html**

Create `openraven-chrome/src/options.html`:

```html
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>OpenRaven Settings</title>
  <style>
    body { max-width: 480px; margin: 32px auto; padding: 0 16px; font-family: system-ui, sans-serif; font-size: 14px; color: #1f1f1f; }
    h1 { font-size: 20px; margin-bottom: 24px; }
    label { display: block; font-size: 12px; color: #6b7280; margin-bottom: 4px; margin-top: 16px; }
    input, select { width: 100%; padding: 8px; border: 1px solid #d1d5db; border-radius: 4px; font-size: 14px; box-sizing: border-box; }
    .btn { padding: 8px 16px; border: none; border-radius: 4px; cursor: pointer; font-size: 14px; margin-top: 16px; }
    .btn-primary { background: #2563eb; color: white; }
    .btn-primary:hover { background: #1d4ed8; }
    .status { margin-top: 12px; padding: 8px; border-radius: 4px; font-size: 12px; }
    .status-ok { background: #d1fae5; color: #065f46; }
    .status-err { background: #fee2e2; color: #991b1b; }
    .hidden { display: none; }
  </style>
</head>
<body>
  <h1>OpenRaven Settings</h1>
  <label for="api-url">API URL</label>
  <input id="api-url" type="url" value="http://localhost:3002" placeholder="http://localhost:3002">
  <label for="auth-mode">Authentication</label>
  <select id="auth-mode">
    <option value="local">Local (no auth)</option>
    <option value="cloud">Cloud (cookie auth)</option>
  </select>
  <div id="cloud-info" class="hidden" style="margin-top:8px; font-size:12px; color:#6b7280;">
    After saving, click the OpenRaven popup and ensure you're logged in at your API URL.
  </div>
  <button class="btn btn-primary" id="save-btn">Save Settings</button>
  <button class="btn" id="test-btn" style="margin-left:8px; background:#e5e7eb;">Test Connection</button>
  <div id="status-msg" class="status hidden"></div>
  <script src="options.js"></script>
</body>
</html>
```

- [ ] **Step 3: Create options.ts**

Create `openraven-chrome/src/options.ts`:

```typescript
const apiUrlInput = document.getElementById("api-url") as HTMLInputElement;
const authModeSelect = document.getElementById("auth-mode") as HTMLSelectElement;
const cloudInfo = document.getElementById("cloud-info") as HTMLDivElement;
const saveBtn = document.getElementById("save-btn") as HTMLButtonElement;
const testBtn = document.getElementById("test-btn") as HTMLButtonElement;
const statusMsg = document.getElementById("status-msg") as HTMLDivElement;

// Load saved settings
chrome.storage.sync.get(["apiUrl", "authMode"], (data) => {
  if (data.apiUrl) apiUrlInput.value = data.apiUrl;
  if (data.authMode) authModeSelect.value = data.authMode;
  toggleCloudInfo();
});

authModeSelect.addEventListener("change", toggleCloudInfo);

function toggleCloudInfo() {
  cloudInfo.classList.toggle("hidden", authModeSelect.value !== "cloud");
}

saveBtn.addEventListener("click", () => {
  chrome.storage.sync.set({
    apiUrl: apiUrlInput.value.replace(/\/+$/, ""),
    authMode: authModeSelect.value,
  }, () => {
    showStatus("Settings saved!", "ok");
  });
});

testBtn.addEventListener("click", async () => {
  const url = apiUrlInput.value.replace(/\/+$/, "");
  try {
    const res = await fetch(`${url}/health`, { signal: AbortSignal.timeout(3000) });
    if (res.ok) showStatus("Connected to OpenRaven!", "ok");
    else showStatus(`Connection failed: HTTP ${res.status}`, "err");
  } catch {
    showStatus("Cannot reach OpenRaven at this URL", "err");
  }
});

function showStatus(msg: string, type: "ok" | "err") {
  statusMsg.textContent = msg;
  statusMsg.className = `status status-${type}`;
  statusMsg.classList.remove("hidden");
}
```

- [ ] **Step 4: Update api.ts for configurable URL and cookie auth**

Replace `openraven-chrome/src/api.ts`:

```typescript
export interface IngestResult {
  files_processed: number;
  entities_extracted: number;
  articles_generated: number;
  errors: string[];
}

export interface Settings {
  apiUrl: string;
  authMode: "local" | "cloud";
}

const DEFAULT_SETTINGS: Settings = { apiUrl: "http://localhost:3002", authMode: "local" };

export async function getSettings(): Promise<Settings> {
  return new Promise((resolve) => {
    chrome.storage.sync.get(["apiUrl", "authMode"], (data) => {
      resolve({
        apiUrl: (data.apiUrl || DEFAULT_SETTINGS.apiUrl).replace(/\/+$/, ""),
        authMode: data.authMode || DEFAULT_SETTINGS.authMode,
      });
    });
  });
}

async function getAuthHeaders(settings: Settings): Promise<Record<string, string>> {
  if (settings.authMode !== "cloud") return {};
  try {
    const url = new URL(settings.apiUrl);
    const cookie = await chrome.cookies.get({ url: settings.apiUrl, name: "session_id" });
    if (cookie) return { Cookie: `session_id=${cookie.value}` };
  } catch {}
  return {};
}

export async function sendToOpenRaven(
  title: string,
  url: string,
  text: string,
): Promise<IngestResult> {
  const settings = await getSettings();
  const markdown = `# ${title}\n\n> Source: ${url}\n\n${text}`;
  const filename = title.replace(/[^a-zA-Z0-9_\- ]/g, "").slice(0, 80).trim() + ".md";

  const formData = new FormData();
  formData.append("files", new Blob([markdown], { type: "text/markdown" }), filename);

  const authHeaders = await getAuthHeaders(settings);
  const response = await fetch(`${settings.apiUrl}/api/ingest`, {
    method: "POST",
    headers: authHeaders,
    body: formData,
  });

  if (!response.ok) {
    throw new Error(`OpenRaven API error: ${response.status}`);
  }

  return response.json();
}

export async function checkConnection(): Promise<{ connected: boolean; authenticated: boolean }> {
  const settings = await getSettings();
  try {
    const res = await fetch(`${settings.apiUrl}/health`, { signal: AbortSignal.timeout(3000) });
    if (!res.ok) return { connected: false, authenticated: false };

    if (settings.authMode === "cloud") {
      const authHeaders = await getAuthHeaders(settings);
      const authRes = await fetch(`${settings.apiUrl}/api/auth/me`, {
        headers: authHeaders,
        signal: AbortSignal.timeout(3000),
      });
      return { connected: true, authenticated: authRes.ok };
    }

    return { connected: true, authenticated: true };
  } catch {
    return { connected: false, authenticated: false };
  }
}
```

- [ ] **Step 5: Update package.json to build options page**

In `openraven-chrome/package.json`, update the build scripts:

```json
{
  "scripts": {
    "build": "bun run build:popup && bun run build:background && bun run build:content && bun run build:options",
    "build:popup": "bun build src/popup.ts --outdir dist --target browser",
    "build:background": "bun build src/background.ts --outdir dist --target browser",
    "build:content": "bun build src/content.ts --outdir dist --target browser",
    "build:options": "bun build src/options.ts --outdir dist --target browser",
    "package": "bun run build && cp manifest.json dist/ && cp -r icons dist/ && cp src/popup.html dist/ && cp src/options.html dist/",
    "test": "bun test tests/"
  }
}
```

- [ ] **Step 6: Build and verify**

```bash
cd /home/ubuntu/source/OpenRaven/openraven-chrome && bun run build 2>&1 | tail -10
```

- [ ] **Step 7: Commit**

```bash
cd /home/ubuntu/source/OpenRaven && git add openraven-chrome/ && git commit -m "$(cat <<'EOF'
feat(m7): add Chrome extension options page with configurable URL and auth

Options page for API URL and auth mode (local/cloud). api.ts uses
chrome.storage.sync for settings, chrome.cookies for session auth.
Manifest updated with cookies, contextMenus, storage permissions.

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 7: Context Menu + Keyboard Shortcut + Selection

**Files:**
- Modify: `openraven-chrome/src/background.ts`
- Modify: `openraven-chrome/src/content.ts`
- Modify: `openraven-chrome/src/popup.ts`
- Modify: `openraven-chrome/src/popup.html`

- [ ] **Step 1: Update background.ts with context menu and keyboard shortcut**

Replace `openraven-chrome/src/background.ts`:

```typescript
import { sendToOpenRaven } from "./api";

// Register context menus on install
chrome.runtime.onInstalled.addListener(() => {
  chrome.contextMenus.create({
    id: "save-page",
    title: "Save page to OpenRaven",
    contexts: ["page"],
  });
  chrome.contextMenus.create({
    id: "save-selection",
    title: "Save selection to OpenRaven",
    contexts: ["selection"],
  });
});

// Handle context menu clicks
chrome.contextMenus.onClicked.addListener(async (info, tab) => {
  if (!tab?.id) return;
  if (info.menuItemId === "save-page") {
    await handleSavePage(tab.id);
  } else if (info.menuItemId === "save-selection" && info.selectionText) {
    const title = tab.title || "Selection";
    const url = tab.url || "";
    try {
      await sendToOpenRaven(title, url, info.selectionText);
    } catch {}
  }
});

// Handle keyboard shortcut
chrome.commands.onCommand.addListener(async (command) => {
  if (command === "save-page") {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    if (tab?.id) await handleSavePage(tab.id);
  }
});

// Handle messages from popup
chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  if (message.type === "SAVE_PAGE") {
    handleSavePage(message.tabId).then(sendResponse).catch((err) =>
      sendResponse({ success: false, error: err.message })
    );
    return true;
  }
});

async function handleSavePage(tabId: number): Promise<{ success: boolean; result?: any; error?: string }> {
  try {
    await chrome.scripting.executeScript({
      target: { tabId },
      files: ["content.js"],
    });

    const [response] = await chrome.tabs.sendMessage(tabId, { type: "EXTRACT_CONTENT" }) as any[];
    if (!response?.text) {
      return { success: false, error: "Could not extract page content" };
    }

    const result = await sendToOpenRaven(response.title, response.url, response.text);
    return { success: true, result };
  } catch (err) {
    return { success: false, error: (err as Error).message };
  }
}
```

- [ ] **Step 2: Update content.ts to support selection extraction**

Replace `openraven-chrome/src/content.ts`:

```typescript
function extractPageContent(): { title: string; url: string; text: string } {
  const article = document.querySelector("article") ?? document.querySelector("main") ?? document.body;

  const clone = article.cloneNode(true) as HTMLElement;
  clone.querySelectorAll("script, style, nav, footer, header, aside, [role='navigation'], [role='banner']").forEach((el) => el.remove());

  const text = clone.innerText
    .split("\n")
    .map((line) => line.trim())
    .filter((line) => line.length > 0)
    .join("\n");

  return {
    title: document.title,
    url: window.location.href,
    text,
  };
}

chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  if (message.type === "EXTRACT_CONTENT") {
    const content = extractPageContent();
    sendResponse(content);
  } else if (message.type === "EXTRACT_SELECTION") {
    const selection = window.getSelection()?.toString() ?? "";
    sendResponse({
      title: document.title,
      url: window.location.href,
      text: selection,
    });
  }
  return true;
});
```

- [ ] **Step 3: Update popup.html with auth status**

In `openraven-chrome/src/popup.html`, add an auth status div after the subtitle div (line 25) and before the save button (line 26):

```html
  <div id="auth-status" class="hidden" style="margin-bottom:8px; padding:4px 8px; border-radius:4px; font-size:11px; background:#fef3c7; color:#92400e;">Not logged in — <a href="#" id="login-link" style="color:#2563eb;">Log in</a></div>
```

- [ ] **Step 4: Update popup.ts to show auth status**

Replace `openraven-chrome/src/popup.ts`:

```typescript
import { checkConnection, getSettings } from "./api";

const saveBtn = document.getElementById("save-btn") as HTMLButtonElement;
const pageTitle = document.getElementById("page-title") as HTMLDivElement;
const statusLoading = document.getElementById("status-loading") as HTMLDivElement;
const statusSuccess = document.getElementById("status-success") as HTMLDivElement;
const statusError = document.getElementById("status-error") as HTMLDivElement;
const errorMessage = document.getElementById("error-message") as HTMLSpanElement;
const statEntities = document.getElementById("stat-entities") as HTMLDivElement;
const statArticles = document.getElementById("stat-articles") as HTMLDivElement;
const statFiles = document.getElementById("stat-files") as HTMLDivElement;
const authStatus = document.getElementById("auth-status") as HTMLDivElement;
const loginLink = document.getElementById("login-link") as HTMLAnchorElement;

function hideAll() {
  statusLoading.classList.add("hidden");
  statusSuccess.classList.add("hidden");
  statusError.classList.add("hidden");
}

function showError(msg: string) {
  hideAll();
  errorMessage.textContent = msg;
  statusError.classList.remove("hidden");
}

function showSuccess(entities: number, articles: number, files: number) {
  hideAll();
  statEntities.textContent = String(entities);
  statArticles.textContent = String(articles);
  statFiles.textContent = String(files);
  statusSuccess.classList.remove("hidden");
}

function showLoading() {
  hideAll();
  statusLoading.classList.remove("hidden");
}

chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
  if (tabs[0]?.title) {
    pageTitle.textContent = tabs[0].title;
  }
});

// Check connection and auth
checkConnection().then(({ connected, authenticated }) => {
  if (!connected) {
    showError("OpenRaven is not running. Check settings.");
    saveBtn.disabled = true;
    return;
  }
  getSettings().then((settings) => {
    if (settings.authMode === "cloud" && !authenticated) {
      authStatus.classList.remove("hidden");
      loginLink.addEventListener("click", (e) => {
        e.preventDefault();
        chrome.tabs.create({ url: `${settings.apiUrl}/login` });
      });
    }
  });
});

saveBtn.addEventListener("click", async () => {
  saveBtn.disabled = true;
  showLoading();

  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (!tab?.id) {
    showError("No active tab");
    saveBtn.disabled = false;
    return;
  }

  chrome.runtime.sendMessage({ type: "SAVE_PAGE", tabId: tab.id }, (response) => {
    if (response?.success) {
      const r = response.result;
      showSuccess(r.entities_extracted, r.articles_generated, r.files_processed);
    } else {
      showError(response?.error ?? "Unknown error");
      saveBtn.disabled = false;
    }
  });
});
```

- [ ] **Step 5: Build and verify**

```bash
cd /home/ubuntu/source/OpenRaven/openraven-chrome && bun run build 2>&1 | tail -10
```

- [ ] **Step 6: Commit**

```bash
cd /home/ubuntu/source/OpenRaven && git add openraven-chrome/ && git commit -m "$(cat <<'EOF'
feat(m7): add context menu, keyboard shortcut, and auth status to extension

Right-click 'Save page/selection to OpenRaven'. Ctrl+Shift+S shortcut.
Popup shows auth status for cloud mode with login link.
Content script supports selection extraction.

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 8: Privacy Policy + Final Build

**Files:**
- Create: `openraven-chrome/PRIVACY.md`

- [ ] **Step 1: Create privacy policy**

Create `openraven-chrome/PRIVACY.md`:

```markdown
# OpenRaven Chrome Extension — Privacy Policy

**Last updated:** 2026-04-05

## What data does this extension access?

When you click "Save to Knowledge Base" or use the context menu, the extension reads the text content of the current web page (or your selected text) and sends it to your configured OpenRaven server.

## Where does the data go?

Your data is sent **only** to the OpenRaven server URL you configure in the extension settings. By default, this is `http://localhost:3002` (your local machine). No data is ever sent to third-party servers, analytics services, or the extension developer.

## What permissions does the extension use?

- **activeTab / scripting**: Read the current page's text content when you click Save
- **cookies**: Read your OpenRaven session cookie for authenticated cloud mode
- **contextMenus**: Add "Save to OpenRaven" to the right-click menu
- **storage**: Save your settings (API URL, auth mode) across browser sessions
- **host_permissions (<all_urls>)**: Required to connect to your configurable OpenRaven server URL

## Data storage

The extension stores only your settings (API URL and auth mode) using Chrome's sync storage. No page content is stored locally by the extension.

## Contact

For questions about this privacy policy, please open an issue at:
https://github.com/chesterkuo/OpenRaven/issues
```

- [ ] **Step 2: Build final package**

```bash
cd /home/ubuntu/source/OpenRaven/openraven-chrome && bun run package 2>&1 | tail -5 && ls -la dist/
```

- [ ] **Step 3: Commit**

```bash
cd /home/ubuntu/source/OpenRaven && git add openraven-chrome/PRIVACY.md && git commit -m "$(cat <<'EOF'
feat(m7): add Chrome extension privacy policy for Web Store

Documents data access, permissions, and storage practices.
No third-party data sharing, all data goes to user's own server.

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 9: Final Integration Test

- [ ] **Step 1: Run all Python tests**

```bash
cd /home/ubuntu/source/OpenRaven/openraven && python3 -m pytest tests/ -v --ignore=tests/benchmark --ignore=tests/fixtures 2>&1 | tail -10
```

- [ ] **Step 2: Build UI**

```bash
cd /home/ubuntu/source/OpenRaven/openraven-ui && bun run build 2>&1 | tail -5
```

- [ ] **Step 3: Build Chrome extension**

```bash
cd /home/ubuntu/source/OpenRaven/openraven-chrome && bun run package 2>&1 | tail -5
```

- [ ] **Step 4: Build Python package**

```bash
cd /home/ubuntu/source/OpenRaven/openraven && python3 -m build 2>&1 | tail -5
```
