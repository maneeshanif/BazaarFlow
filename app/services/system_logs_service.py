"""System logs (PRD F-028): list and open audit rows across shops. Read-only; runs on the platform session."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.problems import NotFound
from app.core.search import escape_like
from app.models.tenant import AuditLog, Tenant
from app.schemas.system_logs import LogDetail, LogRow


def _row(log: AuditLog, tenant_name: str | None) -> dict[str, Any]:
    return {
        "id": log.id,
        "created_at": log.created_at,
        "tenant_id": log.tenant_id,
        "tenant_name": tenant_name,
        "actor_type": log.actor_type,
        "actor_id": log.actor_id,
        "action": log.action,
        "entity": log.entity,
        "entity_id": log.entity_id,
        "request_id": log.request_id,
    }


async def list_logs(
    db: AsyncSession,
    *,
    action: str | None,
    tenant_id: uuid.UUID | None,
    actor_type: str | None,
    since: datetime | None,
    until: datetime | None,
    limit: int,
    offset: int,
) -> tuple[list[LogRow], int]:
    conditions: list[Any] = []
    if action:
        conditions.append(AuditLog.action.ilike(f"%{escape_like(action.strip())}%", escape="\\"))
    if tenant_id:
        conditions.append(AuditLog.tenant_id == tenant_id)
    if actor_type:
        conditions.append(AuditLog.actor_type == actor_type)
    if since:
        conditions.append(AuditLog.created_at >= since)
    if until:
        conditions.append(AuditLog.created_at < until)
    total = (await db.execute(select(func.count()).select_from(AuditLog).where(*conditions))).scalar_one()
    rows = (
        await db.execute(
            select(AuditLog, Tenant.name)
            .outerjoin(Tenant, Tenant.id == AuditLog.tenant_id)
            .where(*conditions)
            .order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
            .limit(limit)
            .offset(offset)
        )
    ).all()
    return [LogRow(**_row(log, name)) for log, name in rows], int(total)


async def get_log(db: AsyncSession, log_id: uuid.UUID) -> LogDetail:
    found = (
        await db.execute(select(AuditLog, Tenant.name).outerjoin(Tenant, Tenant.id == AuditLog.tenant_id).where(AuditLog.id == log_id))
    ).first()
    if found is None:
        raise NotFound("Log entry")
    log, name = found
    return LogDetail(**_row(log, name), before=log.before_json, after=log.after_json)
