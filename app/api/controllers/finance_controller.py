"""Finance API (PRD F-013, D-002): the overview and cash book for owners and managers, the dashboard for owners."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import MANAGER_UP, OWNER_ONLY, get_tenant_db, require_role
from app.core.pagination import DEFAULT_LIMIT, MAX_LIMIT, Page, decode_cursor, next_cursor
from app.core.tenancy import Principal
from app.schemas.dashboard import DashboardRange
from app.schemas.finance import CashBookEntry, FinanceOverview
from app.services import finance_report_service

router = APIRouter()

TenantDb = Annotated[AsyncSession, Depends(get_tenant_db, scope="function")]


@router.get("/overview", response_model=FinanceOverview)
async def overview(
    principal: Annotated[Principal, Depends(require_role(*MANAGER_UP))],
    db: TenantDb,
    range_: Annotated[DashboardRange, Query(alias="range")] = "30d",
) -> FinanceOverview:
    """F-013. A manager gets the revenue, the cash/credit split and the receivables; the owner also gets margin and payables."""
    return await finance_report_service.overview(db, principal, range_)


@router.get("/dashboard", response_model=FinanceOverview)
async def dashboard(
    principal: Annotated[Principal, Depends(require_role(*OWNER_ONLY))],
    db: TenantDb,
    range_: Annotated[DashboardRange, Query(alias="range")] = "30d",
) -> FinanceOverview:
    """D-002: the owner's finance dashboard (all five KPIs)."""
    return await finance_report_service.overview(db, principal, range_)


@router.get("/ledger", response_model=Page[CashBookEntry])
async def cash_book(
    principal: Annotated[Principal, Depends(require_role(*MANAGER_UP))],
    db: TenantDb,
    direction: Literal["in", "out"] | None = None,
    since: datetime | None = None,
    until: datetime | None = None,
    limit: Annotated[int, Query(ge=1, le=MAX_LIMIT)] = DEFAULT_LIMIT,
    cursor: Annotated[str | None, Query(max_length=60)] = None,
) -> Page[CashBookEntry]:
    offset = decode_cursor(cursor)
    items, total = await finance_report_service.cash_book(
        db, principal.tenant_id, direction=direction, since=since, until=until, limit=limit, offset=offset
    )
    return Page[CashBookEntry](items=items, total=total, next_cursor=next_cursor(offset, limit, total))
