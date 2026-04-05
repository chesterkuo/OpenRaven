"""Account deletion and knowledge base export."""
from __future__ import annotations

import json
import logging
import shutil
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import delete, select, func
from sqlalchemy.engine import Engine

from openraven.auth.db import (
    users, sessions, tenants, tenant_members, audit_logs,
    invitations, password_reset_tokens,
)

logger = logging.getLogger(__name__)


def check_deletion_eligibility(engine: Engine, user_id: str) -> dict:
    """Check if user can delete their account."""
    with engine.connect() as conn:
        tenant_row = conn.execute(
            select(tenants.c.id).where(tenants.c.owner_user_id == user_id)
        ).first()

        if not tenant_row:
            return {"eligible": True, "reason": "", "tenant_id": None, "member_count": 0}

        tenant_id = tenant_row.id
        member_count = conn.execute(
            select(func.count()).select_from(tenant_members)
            .where(tenant_members.c.tenant_id == tenant_id)
        ).scalar() or 0

        if member_count > 1:
            return {
                "eligible": False,
                "reason": f"Remove all {member_count - 1} team member(s) before deleting your account",
                "tenant_id": tenant_id,
                "member_count": member_count,
            }

        return {"eligible": True, "reason": "", "tenant_id": tenant_id, "member_count": member_count}


def delete_account(engine: Engine, user_id: str, tenant_id: str | None, data_dir: Path) -> None:
    """Permanently delete a user account and all associated data."""
    if data_dir.exists():
        shutil.rmtree(data_dir, ignore_errors=True)

    with engine.connect() as conn:
        if tenant_id:
            conn.execute(delete(audit_logs).where(audit_logs.c.tenant_id == tenant_id))
            conn.execute(delete(invitations).where(invitations.c.tenant_id == tenant_id))
            conn.execute(delete(tenant_members).where(tenant_members.c.tenant_id == tenant_id))
            conn.execute(delete(tenants).where(tenants.c.id == tenant_id))

        conn.execute(delete(sessions).where(sessions.c.user_id == user_id))
        conn.execute(delete(password_reset_tokens).where(password_reset_tokens.c.user_id == user_id))
        conn.execute(delete(tenant_members).where(tenant_members.c.user_id == user_id))
        conn.execute(delete(users).where(users.c.id == user_id))
        conn.commit()

    logger.info(f"Account deleted: user_id={user_id}, tenant_id={tenant_id}")


def export_knowledge_base(data_dir: Path, output_dir: Path) -> Path:
    """Create a zip export of the knowledge base."""
    output_dir.mkdir(parents=True, exist_ok=True)
    zip_path = output_dir / "openraven_export.zip"

    wiki_dir = data_dir / "wiki"
    graphml_path = data_dir / "lightrag_data" / "graph_chunk_entity_relation.graphml"

    file_count = 0
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        if wiki_dir.exists():
            for f in sorted(wiki_dir.glob("*.md")):
                zf.write(f, f.name)
                file_count += 1
        if graphml_path.exists():
            zf.write(graphml_path, "knowledge_graph.graphml")
        meta = {"exported_at": datetime.now(timezone.utc).isoformat(), "file_count": file_count}
        zf.writestr("metadata.json", json.dumps(meta, indent=2))

    return zip_path
