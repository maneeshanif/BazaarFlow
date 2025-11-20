"""REST endpoints for live log streaming."""

from __future__ import annotations

from fastapi import APIRouter, Query

from ..utils.live_logs import get_recent_logs

router = APIRouter(prefix="/api/logs", tags=["logs"])


@router.get("")
async def list_logs(
    limit: int = Query(default=100, ge=1, le=500),
    action: str | None = Query(default=None, min_length=1),
    logger: str | None = Query(default=None, min_length=1),
):
    logs = get_recent_logs(limit=limit, action=action, logger_name=logger)
    return {"ok": True, "logs": logs}
