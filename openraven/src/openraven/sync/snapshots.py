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
        wiki_dir = data_dir / "wiki"
        if wiki_dir.exists():
            for f in sorted(wiki_dir.rglob("*")):
                if f.is_file():
                    zf.write(f, f"wiki/{f.relative_to(wiki_dir)}")

        lightrag_dir = data_dir / "lightrag_data"
        if lightrag_dir.exists():
            for f in sorted(lightrag_dir.rglob("*")):
                if f.is_file():
                    zf.write(f, f"lightrag_data/{f.relative_to(lightrag_dir)}")

        meta = {
            "created_at": datetime.now(timezone.utc).isoformat(),
            "source_dir": str(data_dir),
        }
        zf.writestr("snapshot_meta.json", json.dumps(meta, indent=2))

    return zip_path


def restore_snapshot(zip_path: Path, data_dir: Path) -> None:
    """Extract a snapshot zip to data_dir. Validates paths to prevent zip-slip."""
    data_dir.mkdir(parents=True, exist_ok=True)
    resolved_root = data_dir.resolve()
    with zipfile.ZipFile(zip_path, "r") as zf:
        for member in zf.infolist():
            target = (data_dir / member.filename).resolve()
            if not target.is_relative_to(resolved_root):
                raise ValueError(f"Zip-slip detected: {member.filename}")
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
