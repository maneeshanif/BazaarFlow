"""Sales and orders API (PRD F-007, F-008, §13.2): role gate -> tenant-scoped session -> service -> audit.

``POST /sales`` posts a sale and accepts an ``Idempotency-Key`` so a retried request returns the order it already made.
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import ALL_ROLES, MANAGER_UP, get_tenant_db, require_role
from app.core.pagination import DEFAULT_LIMIT, MAX_LIMIT, Page, decode_cursor, next_cursor
from app.core.tenancy import Principal
from app.schemas.order import OrderDetail, OrderSummary, ReverseRequest, SaleCreate, SalePreview, SalePreviewRequest
from app.services import order_service

sales_router = APIRouter()
orders_router = APIRouter()

TenantDb = Annotated[AsyncSession, Depends(get_tenant_db, scope="function")]


@sales_router.post("/", response_model=OrderDetail, status_code=status.HTTP_201_CREATED)
async def post_sale(
    body: SaleCreate,
    response: Response,
    principal: Annotated[Principal, Depends(require_role(*ALL_ROLES))],
    db: TenantDb,
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key", min_length=8, max_length=80)] = None,
) -> OrderDetail:
    order, created = await order_service.post_sale(db, principal, body, idempotency_key=idempotency_key)
    if not created:
        response.status_code = status.HTTP_200_OK  # a retry: the sale already exists
    return order


@sales_router.post("/preview", response_model=SalePreview)
async def preview_sale(
    body: SalePreviewRequest, principal: Annotated[Principal, Depends(require_role(*ALL_ROLES))], db: TenantDb
) -> SalePreview:
    """Add up a sale for the form (prices, totals, stock) without writing anything."""
    return await order_service.preview_sale(db, principal, body)


@orders_router.get("/", response_model=Page[OrderSummary])
async def list_orders(
    principal: Annotated[Principal, Depends(require_role(*ALL_ROLES))],
    db: TenantDb,
    status_filter: Annotated[str | None, Query(alias="status", pattern="^(draft|posted|reversed|cancelled)$")] = None,
    channel: Annotated[str | None, Query(pattern="^(pos|chat|whatsapp|voice)$")] = None,
    customer_id: UUID | None = None,
    q: Annotated[str | None, Query(max_length=80)] = None,
    sort: Annotated[str, Query(max_length=20)] = "-created_at",
    limit: Annotated[int, Query(ge=1, le=MAX_LIMIT)] = DEFAULT_LIMIT,
    cursor: Annotated[str | None, Query(max_length=60)] = None,
) -> Page[OrderSummary]:
    offset = decode_cursor(cursor)
    items, total = await order_service.list_orders(
        db,
        principal,
        status=status_filter,
        channel=channel,
        customer_id=customer_id,
        q=q,
        sort=sort,
        limit=limit,
        offset=offset,
    )
    return Page[OrderSummary](items=items, total=total, next_cursor=next_cursor(offset, limit, total))


@orders_router.get("/{order_id}", response_model=OrderDetail)
async def get_order(order_id: UUID, principal: Annotated[Principal, Depends(require_role(*ALL_ROLES))], db: TenantDb) -> OrderDetail:
    return await order_service.get_order(db, principal, order_id)


@orders_router.post("/{order_id}/reverse", response_model=OrderDetail)
async def reverse_order(
    order_id: UUID,
    body: ReverseRequest,
    principal: Annotated[Principal, Depends(require_role(*MANAGER_UP))],
    db: TenantDb,
) -> OrderDetail:
    """Undo a posted sale (PRD §13.2: reversing is a manager's decision). Stock, payments and udhaar are put back."""
    return await order_service.reverse_order(db, principal, order_id, body)
