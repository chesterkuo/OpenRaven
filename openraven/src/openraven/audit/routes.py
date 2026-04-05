"""Audit log API routes."""
from __future__ import annotations

import csv
import io
from datetime import datetime

from fastapi import APIRouter, Query, Request, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.engine import Engine

from openraven.audit.logger import query_audit_logs, count_audit_logs


def _sanitize_csv_cell(value: str) -> str:
    """Prevent CSV formula injection (OWASP)."""
    if value and value[0] in ("=", "+", "-", "@", "\t", "\r"):
        return "'" + value
    return value


def create_audit_router(engine: Engine) -> APIRouter:
    router = APIRouter()

    def _get_tenant_id(request: Request) -> str:
        auth = getattr(request.state, "auth", None)
        if not auth:
            raise HTTPException(401, "Not authenticated")
        return auth.tenant_id

    @router.get("/")
    async def list_audit_logs(
        request: Request,
        action: str | None = Query(default=None),
        user_id: str | None = Query(default=None),
        from_date: str | None = Query(default=None, alias="from"),
        to_date: str | None = Query(default=None, alias="to"),
        limit: int = Query(default=100, ge=1, le=1000),
        offset: int = Query(default=0, ge=0),
    ):
        tenant_id = _get_tenant_id(request)
        from_ts = datetime.fromisoformat(from_date) if from_date else None
        to_ts = datetime.fromisoformat(to_date) if to_date else None

        logs = query_audit_logs(
            engine, tenant_id=tenant_id, action=action, user_id=user_id,
            from_ts=from_ts, to_ts=to_ts, limit=limit, offset=offset,
        )
        total = count_audit_logs(
            engine, tenant_id=tenant_id, action=action, user_id=user_id,
            from_ts=from_ts, to_ts=to_ts,
        )
        return {"logs": logs, "total": total, "limit": limit, "offset": offset}

    @router.get("/export")
    async def export_audit_logs(
        request: Request,
        action: str | None = Query(default=None),
        user_id: str | None = Query(default=None),
        from_date: str | None = Query(default=None, alias="from"),
        to_date: str | None = Query(default=None, alias="to"),
    ):
        tenant_id = _get_tenant_id(request)
        from_ts = datetime.fromisoformat(from_date) if from_date else None
        to_ts = datetime.fromisoformat(to_date) if to_date else None

        logs = query_audit_logs(
            engine, tenant_id=tenant_id, action=action, user_id=user_id,
            from_ts=from_ts, to_ts=to_ts, limit=10000, offset=0,
        )

        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=["timestamp", "user_id", "action", "details", "ip_address"])
        writer.writeheader()
        for log in logs:
            writer.writerow({
                "timestamp": _sanitize_csv_cell(log["timestamp"] or ""),
                "user_id": _sanitize_csv_cell(log["user_id"] or ""),
                "action": _sanitize_csv_cell(log["action"]),
                "details": _sanitize_csv_cell(log["details"] or ""),
                "ip_address": _sanitize_csv_cell(log["ip_address"] or ""),
            })

        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=audit_logs.csv"},
        )

    return router
