"""Sync API routes for E2EE cloud sync."""
from __future__ import annotations

import json
import os
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Request, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy import select, insert as sa_insert, update as sa_update
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

    _SNAPSHOT_ID_RE = __import__("re").compile(r"^\d{4}-\d{2}-\d{2}T\d{6}_[0-9a-f]{6}$")

    def _get_auth(request: Request):
        auth = getattr(request.state, "auth", None)
        if not auth:
            raise HTTPException(401, "Not authenticated")
        return auth

    def _validate_snapshot_id(snapshot_id: str) -> None:
        """Reject snapshot IDs that don't match the expected pattern (path traversal protection)."""
        if not _SNAPSHOT_ID_RE.match(snapshot_id):
            raise HTTPException(400, "Invalid snapshot ID")

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
        if len(body.passphrase) < 8:
            raise HTTPException(400, "Passphrase must be at least 8 characters")
        pw_hash = hash_password(body.passphrase)
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

        snap_dir = Path(tempfile.mkdtemp())
        try:
            zip_path = create_snapshot(data_dir, snap_dir)
            plaintext = zip_path.read_bytes()
            ciphertext, salt, iv = encrypt_blob(plaintext, body.passphrase)

            sync_dir = sync_root / auth.tenant_id
            sync_dir.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H%M%S") + "_" + os.urandom(3).hex()
            enc_path = sync_dir / f"{timestamp}.enc"
            meta_path = sync_dir / f"{timestamp}.meta"
            enc_path.write_bytes(ciphertext)
            meta_path.write_text(json.dumps({
                "salt_hex": salt.hex(),
                "iv_hex": iv.hex(),
                "size": len(ciphertext),
                "created_at": datetime.now(timezone.utc).isoformat(),
            }), encoding="utf-8")

            with engine.connect() as conn:
                conn.execute(
                    sa_update(sync_config)
                    .where(sync_config.c.tenant_id == auth.tenant_id)
                    .values(last_sync_at=datetime.now(timezone.utc))
                )
                conn.commit()
        finally:
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

        if body.snapshot_id:
            snap = next((s for s in snapshots if s["id"] == body.snapshot_id), None)
            if not snap:
                raise HTTPException(404, "Snapshot not found")
        else:
            snap = snapshots[0]

        enc_path = sync_dir / f"{snap['id']}.enc"
        ciphertext = enc_path.read_bytes()
        salt = bytes.fromhex(snap["salt_hex"])
        iv = bytes.fromhex(snap["iv_hex"])

        try:
            plaintext = decrypt_blob(ciphertext, body.passphrase, salt, iv)
        except ValueError:
            raise HTTPException(403, "Incorrect passphrase — cannot decrypt snapshot")

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
        _validate_snapshot_id(snapshot_id)
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
