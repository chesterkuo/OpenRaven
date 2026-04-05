import pytest


def test_derive_key_deterministic():
    from openraven.sync.crypto import derive_key
    salt = b"\x00" * 16
    key1 = derive_key("mypassphrase", salt)
    key2 = derive_key("mypassphrase", salt)
    assert key1 == key2
    assert len(key1) == 32


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
    assert salt1 != salt2 or iv1 != iv2
    assert ct1 != ct2


import json
import zipfile
from pathlib import Path


def test_create_snapshot(tmp_path):
    from openraven.sync.snapshots import create_snapshot
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
    src = tmp_path / "src"
    wiki_dir = src / "wiki"
    wiki_dir.mkdir(parents=True)
    (wiki_dir / "article.md").write_text("# Original")
    zip_path = create_snapshot(src, tmp_path / "snap")

    dest = tmp_path / "dest"
    dest.mkdir()
    restore_snapshot(zip_path, dest)
    assert (dest / "wiki" / "article.md").read_text() == "# Original"


def test_list_snapshots(tmp_path):
    from openraven.sync.snapshots import list_snapshots
    sync_dir = tmp_path / "sync"
    sync_dir.mkdir()
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
    assert result[0]["size"] == 2048


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
    ct = res.headers.get("content-type", "")
    assert "zip" in ct or "octet" in ct


def test_api_sync_status(app_with_sync):
    client = TestClient(app_with_sync)
    res = client.get("/api/sync/status")
    assert res.status_code == 200
    data = res.json()
    assert data["configured"] is False
    assert data["snapshot_count"] == 0
