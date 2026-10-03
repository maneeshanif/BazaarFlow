"""Home dashboard API (PRD F-004, D-001): every signed-in role, figures filtered by role in the service."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import ALL_ROLES, get_tenant_db, require_role
from app.core.tenancy import Principal
from app.schemas.dashboard import DashboardOut, DashboardRange
from app.services import dashboard_service

router = APIRouter()

TenantDb = Annotated[AsyncSession, Depends(get_tenant_db, scope="function")]
Anyone = Annotated[Principal, Depends(require_role(*ALL_ROLES))]


@router.get("/summary", response_model=DashboardOut)
async def summary(principal: Anyone, db: TenantDb, range_: Annotated[DashboardRange, Query(alias="range")] = "today") -> DashboardOut:
    return await dashboard_service.summary(db, principal, range_)
