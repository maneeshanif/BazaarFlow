"""Platform admin API (PRD F-025, D-004): BazaarFlow operators only.

Every route sits behind ``require_platform_admin`` and runs on ``get_platform_db`` (cross-tenant, one audit row per
request). The only change an operator can make is to suspend or reactivate a shop.
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_platform_db, require_platform_admin
from app.core.pagination import DEFAULT_LIMIT, MAX_LIMIT, Page, decode_cursor, next_cursor
from app.core.tenancy import Principal
from app.schemas.platform import PlatformOverview, PlatformTenantOut, SuspendRequest, TenantStatus
from app.schemas.system_logs import LogDetail, LogRow
from app.services import platform_service, system_logs_service

router = APIRouter()

PlatformDb = Annotated[AsyncSession, Depends(get_platform_db, scope="function")]
Operator = Annotated[Principal, Depends(require_platform_admin)]


@router.get("/overview", response_model=PlatformOverview)
async def overview(principal: Operator, db: PlatformDb) -> PlatformOverview:
    """D-004."""
    return await platform_service.overview(db)


@router.get("/tenants", response_model=Page[PlatformTenantOut])
async def list_tenants(
    principal: Operator,
    db: PlatformDb,
    q: Annotated[str | None, Query(max_length=80)] = None,
    status: TenantStatus | None = None,
    include_demo: bool = False,
    limit: Annotated[int, Query(ge=1, le=MAX_LIMIT)] = DEFAULT_LIMIT,
    cursor: Annotated[str | None, Query(max_length=60)] = None,
) -> Page[PlatformTenantOut]:
    offset = decode_cursor(cursor)
    items, total = await platform_service.list_tenants(db, q=q, status=status, include_demo=include_demo, limit=limit, offset=offset)
    return Page[PlatformTenantOut](items=items, total=total, next_cursor=next_cursor(offset, limit, total))


@router.get("/tenants/{tenant_id}", response_model=PlatformTenantOut)
async def get_tenant(tenant_id: UUID, principal: Operator, db: PlatformDb) -> PlatformTenantOut:
    return await platform_service.get_tenant(db, tenant_id)


@router.post("/tenants/{tenant_id}/suspend", response_model=PlatformTenantOut)
async def suspend_tenant(tenant_id: UUID, body: SuspendRequest, principal: Operator, db: PlatformDb) -> PlatformTenantOut:
    return await platform_service.set_status(db, principal, tenant_id, status="suspended", reason=body.reason)


@router.post("/tenants/{tenant_id}/reactivate", response_model=PlatformTenantOut)
async def reactivate_tenant(tenant_id: UUID, principal: Operator, db: PlatformDb) -> PlatformTenantOut:
    return await platform_service.set_status(db, principal, tenant_id, status="active", reason=None)


@router.get("/logs", response_model=Page[LogRow])
async def list_logs(
    principal: Operator,
    db: PlatformDb,
    action: Annotated[str | None, Query(max_length=80)] = None,
    tenant_id: UUID | None = None,
    actor_type: Literal["user", "agent", "system"] | None = None,
    since: datetime | None = None,
    until: datetime | None = None,
    limit: Annotated[int, Query(ge=1, le=MAX_LIMIT)] = DEFAULT_LIMIT,
    cursor: Annotated[str | None, Query(max_length=60)] = None,
) -> Page[LogRow]:
    """F-028: the audit trail across shops, newest first."""
    offset = decode_cursor(cursor)
    items, total = await system_logs_service.list_logs(
        db, action=action, tenant_id=tenant_id, actor_type=actor_type, since=since, until=until, limit=limit, offset=offset
    )
    return Page[LogRow](items=items, total=total, next_cursor=next_cursor(offset, limit, total))


@router.get("/logs/{log_id}", response_model=LogDetail)
async def get_log(log_id: UUID, principal: Operator, db: PlatformDb) -> LogDetail:
    return await system_logs_service.get_log(db, log_id)
