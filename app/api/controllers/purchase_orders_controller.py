"""Draft purchase orders API (PRD W-006): owners and managers read them and cancel a draft.

Orders are drafted by the low-stock recipe, so there is no create or edit route. Role gate -> tenant-scoped session ->
service -> audit.
"""

from __future__ import annotations

from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import MANAGER_UP, get_tenant_db, require_role
from app.core.pagination import DEFAULT_LIMIT, MAX_LIMIT, Page, decode_cursor, next_cursor
from app.core.tenancy import Principal
from app.schemas.purchase_orders import PurchaseOrderDetail, PurchaseOrderOut
from app.services import purchase_order_service

router = APIRouter()

TenantDb = Annotated[AsyncSession, Depends(get_tenant_db, scope="function")]


@router.get("/", response_model=Page[PurchaseOrderOut])
async def list_purchase_orders(
    principal: Annotated[Principal, Depends(require_role(*MANAGER_UP))],
    db: TenantDb,
    status: Literal["drafted", "approved", "sent", "cancelled"] | None = None,
    limit: Annotated[int, Query(ge=1, le=MAX_LIMIT)] = DEFAULT_LIMIT,
    cursor: Annotated[str | None, Query(max_length=60)] = None,
) -> Page[PurchaseOrderOut]:
    offset = decode_cursor(cursor)
    items, total = await purchase_order_service.list_orders(db, principal, status=status, limit=limit, offset=offset)
    return Page[PurchaseOrderOut](items=items, total=total, next_cursor=next_cursor(offset, limit, total))


@router.get("/{order_id}", response_model=PurchaseOrderDetail)
async def get_purchase_order(
    order_id: UUID, principal: Annotated[Principal, Depends(require_role(*MANAGER_UP))], db: TenantDb
) -> PurchaseOrderDetail:
    return await purchase_order_service.get_order(db, principal, order_id)


@router.post("/{order_id}/cancel", response_model=PurchaseOrderDetail)
async def cancel_purchase_order(
    order_id: UUID, principal: Annotated[Principal, Depends(require_role(*MANAGER_UP))], db: TenantDb
) -> PurchaseOrderDetail:
    return await purchase_order_service.cancel(db, principal, order_id)
