"""Marketing schedule and activity API (PRD F-015, F-016): owners and managers."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import MANAGER_UP, get_tenant_db, require_role
from app.core.pagination import DEFAULT_LIMIT, MAX_LIMIT, Page, decode_cursor, next_cursor
from app.core.tenancy import Principal
from app.schemas.marketing_schedule import ActivityOut, ActivityStatus, ScheduleIn, ScheduleOut, ScheduleRequest
from app.services import marketing_schedule_service

router = APIRouter()

TenantDb = Annotated[AsyncSession, Depends(get_tenant_db, scope="function")]
Manager = Annotated[Principal, Depends(require_role(*MANAGER_UP))]


@router.get("/schedule", response_model=ScheduleOut)
async def get_schedule(principal: Manager, db: TenantDb) -> ScheduleOut:
    return await marketing_schedule_service.get_schedule(db, principal)


@router.put("/schedule", response_model=ScheduleOut)
async def put_schedule(body: ScheduleIn, principal: Manager, db: TenantDb) -> ScheduleOut:
    return await marketing_schedule_service.put_schedule(db, principal, body)


@router.get("/activity", response_model=Page[ActivityOut])
async def list_activity(
    principal: Manager,
    db: TenantDb,
    status: ActivityStatus | None = None,
    limit: Annotated[int, Query(ge=1, le=MAX_LIMIT)] = DEFAULT_LIMIT,
    cursor: Annotated[str | None, Query(max_length=60)] = None,
) -> Page[ActivityOut]:
    offset = decode_cursor(cursor)
    items, total = await marketing_schedule_service.list_activity(db, principal, status=status, limit=limit, offset=offset)
    return Page[ActivityOut](items=items, total=total, next_cursor=next_cursor(offset, limit, total))


@router.post("/activity/{post_id}/queue", response_model=ActivityOut)
async def queue_post(post_id: UUID, body: ScheduleRequest, principal: Manager, db: TenantDb) -> ActivityOut:
    return await marketing_schedule_service.queue_post(db, principal, post_id, body.scheduled_for)


@router.post("/activity/{post_id}/retry", response_model=ActivityOut)
async def retry_post(post_id: UUID, principal: Manager, db: TenantDb) -> ActivityOut:
    return await marketing_schedule_service.retry_post(db, principal, post_id)


@router.post("/activity/{post_id}/cancel", response_model=ActivityOut)
async def cancel_post(post_id: UUID, principal: Manager, db: TenantDb) -> ActivityOut:
    return await marketing_schedule_service.cancel_post(db, principal, post_id)
