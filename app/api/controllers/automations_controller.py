"""Automation recipes API (PRD F-024, §13.2): owners and managers."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import MANAGER_UP, get_tenant_db, require_role
from app.core.pagination import DEFAULT_LIMIT, MAX_LIMIT, Page, decode_cursor, next_cursor
from app.core.tenancy import Principal
from app.schemas.automations import AutomationOut, RunOut, RunStatus, ToggleRequest
from app.services import automation_service

router = APIRouter()

TenantDb = Annotated[AsyncSession, Depends(get_tenant_db, scope="function")]
Manager = Annotated[Principal, Depends(require_role(*MANAGER_UP))]


@router.get("/", response_model=list[AutomationOut])
async def list_automations(principal: Manager, db: TenantDb) -> list[AutomationOut]:
    return await automation_service.list_automations(db, principal)


@router.get("/runs", response_model=Page[RunOut])
async def list_runs(
    principal: Manager,
    db: TenantDb,
    automation: Annotated[str | None, Query(max_length=40)] = None,
    status: RunStatus | None = None,
    limit: Annotated[int, Query(ge=1, le=MAX_LIMIT)] = DEFAULT_LIMIT,
    cursor: Annotated[str | None, Query(max_length=60)] = None,
) -> Page[RunOut]:
    """Declared before ``/{key}`` so ``runs`` is not read as a recipe key."""
    offset = decode_cursor(cursor)
    items, total = await automation_service.list_runs(db, principal, key=automation, status=status, limit=limit, offset=offset)
    return Page[RunOut](items=items, total=total, next_cursor=next_cursor(offset, limit, total))


@router.post("/{key}/toggle", response_model=AutomationOut)
async def toggle(key: str, body: ToggleRequest, principal: Manager, db: TenantDb) -> AutomationOut:
    return await automation_service.toggle(db, principal, key, body.enabled)


@router.post("/{key}/run", response_model=RunOut)
async def run_now(key: str, principal: Manager, db: TenantDb) -> RunOut:
    """Run a switched-on recipe once, now. Safe to repeat: nothing is sent twice."""
    return await automation_service.run_now(db, principal, key)
