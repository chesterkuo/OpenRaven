"""Audit logging for SaaS mode (PostgreSQL-backed)."""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

from sqlalchemy import insert, select, desc, func
from sqlalchemy.engine import Engine

from openraven.auth.db import audit_logs

logger = logging.getLogger(__name__)


def log_action(
    engine: Engine | None,
    user_id: str | None,
    tenant_id: str | None,
    action: str,
    details: dict | None = None,
    ip_address: str = "",
) -> None:
    """Insert an audit log entry. No-op if engine is None. Never raises."""
    if engine is None:
        return
    try:
        with engine.connect() as conn:
            conn.execute(insert(audit_logs).values(
                user_id=user_id,
                tenant_id=tenant_id,
                action=action,
                details=json.dumps(details) if details else None,
                ip_address=ip_address,
                timestamp=datetime.now(timezone.utc),
            ))
            conn.commit()
    except Exception as e:
        logger.error(f"Audit log failed: {e}")


def query_audit_logs(
    engine: Engine,
    tenant_id: str,
    action: str | None = None,
    user_id: str | None = None,
    from_ts: datetime | None = None,
    to_ts: datetime | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[dict]:
    """Query audit logs with optional filters. Returns list of dicts."""
    stmt = select(audit_logs).where(audit_logs.c.tenant_id == tenant_id)

    if action:
        stmt = stmt.where(audit_logs.c.action == action)
    if user_id:
        stmt = stmt.where(audit_logs.c.user_id == user_id)
    if from_ts:
        stmt = stmt.where(audit_logs.c.timestamp >= from_ts)
    if to_ts:
        stmt = stmt.where(audit_logs.c.timestamp <= to_ts)

    stmt = stmt.order_by(desc(audit_logs.c.timestamp)).limit(limit).offset(offset)

    with engine.connect() as conn:
        rows = conn.execute(stmt).fetchall()

    return [
        {
            "id": row.id,
            "user_id": row.user_id,
            "tenant_id": row.tenant_id,
            "action": row.action,
            "details": row.details,
            "ip_address": row.ip_address,
            "timestamp": row.timestamp.isoformat() if row.timestamp else None,
        }
        for row in rows
    ]


def count_audit_logs(
    engine: Engine,
    tenant_id: str,
    action: str | None = None,
    user_id: str | None = None,
    from_ts: datetime | None = None,
    to_ts: datetime | None = None,
) -> int:
    """Count audit logs matching filters."""
    stmt = select(func.count()).select_from(audit_logs).where(audit_logs.c.tenant_id == tenant_id)
    if action:
        stmt = stmt.where(audit_logs.c.action == action)
    if user_id:
        stmt = stmt.where(audit_logs.c.user_id == user_id)
    if from_ts:
        stmt = stmt.where(audit_logs.c.timestamp >= from_ts)
    if to_ts:
        stmt = stmt.where(audit_logs.c.timestamp <= to_ts)

    with engine.connect() as conn:
        return conn.execute(stmt).scalar() or 0
