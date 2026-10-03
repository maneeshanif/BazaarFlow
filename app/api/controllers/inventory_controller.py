"""Products and stock API (PRD F-010, §13.2): role gate -> tenant-scoped session -> service -> audit.

Controllers stay thin: validation lives in the schemas, rules in ``product_service`` / ``stock_service``.
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import ALL_ROLES, MANAGER_UP, OWNER_ONLY, get_tenant_db, require_role
from app.core.pagination import DEFAULT_LIMIT, MAX_LIMIT, Page, decode_cursor, next_cursor
from app.core.tenancy import Principal
from app.schemas.product import (
    ProductCreate,
    ProductOut,
    ProductUpdate,
    StockMovementCreate,
    StockMovementOut,
)
from app.services import product_service, stock_service

router = APIRouter()

TenantDb = Annotated[AsyncSession, Depends(get_tenant_db, scope="function")]


@router.get("/", response_model=Page[ProductOut])
async def list_products(
    principal: Annotated[Principal, Depends(require_role(*ALL_ROLES))],
    db: TenantDb,
    q: Annotated[str | None, Query(max_length=80)] = None,
    category: Annotated[str | None, Query(max_length=60)] = None,
    active: bool | None = None,
    low_stock: bool | None = None,
    sort: Annotated[str, Query(max_length=20)] = "name",
    limit: Annotated[int, Query(ge=1, le=MAX_LIMIT)] = DEFAULT_LIMIT,
    cursor: Annotated[str | None, Query(max_length=60)] = None,
) -> Page[ProductOut]:
    offset = decode_cursor(cursor)
    items, total = await product_service.list_products(
        db, principal, q=q, category=category, active=active, low_stock=low_stock, sort=sort, limit=limit, offset=offset
    )
    return Page[ProductOut](items=items, total=total, next_cursor=next_cursor(offset, limit, total))


@router.post("/", response_model=ProductOut, status_code=status.HTTP_201_CREATED)
async def create_product(
    body: ProductCreate,
    principal: Annotated[Principal, Depends(require_role(*MANAGER_UP))],
    db: TenantDb,
) -> ProductOut:
    return await product_service.create_product(db, principal, body)


@router.get("/{product_id}", response_model=ProductOut)
async def get_product(
    product_id: UUID, principal: Annotated[Principal, Depends(require_role(*ALL_ROLES))], db: TenantDb
) -> ProductOut:
    return await product_service.get_product(db, principal, product_id)


@router.patch("/{product_id}", response_model=ProductOut)
async def update_product(
    product_id: UUID,
    body: ProductUpdate,
    principal: Annotated[Principal, Depends(require_role(*MANAGER_UP))],
    db: TenantDb,
) -> ProductOut:
    return await product_service.update_product(db, principal, product_id, body)


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product(
    product_id: UUID, principal: Annotated[Principal, Depends(require_role(*OWNER_ONLY))], db: TenantDb
) -> Response:
    await product_service.delete_product(db, principal, product_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{product_id}/stock-movements", response_model=ProductOut, status_code=status.HTTP_201_CREATED)
async def add_stock_movement(
    product_id: UUID,
    body: StockMovementCreate,
    principal: Annotated[Principal, Depends(require_role(*MANAGER_UP))],
    db: TenantDb,
) -> ProductOut:
    return await product_service.add_manual_movement(
        db, principal, product_id, delta=body.delta, reason=body.reason, note=body.note
    )


@router.get("/{product_id}/stock-movements", response_model=Page[StockMovementOut])
async def list_stock_movements(
    product_id: UUID,
    principal: Annotated[Principal, Depends(require_role(*MANAGER_UP))],
    db: TenantDb,
    limit: Annotated[int, Query(ge=1, le=MAX_LIMIT)] = DEFAULT_LIMIT,
    cursor: Annotated[str | None, Query(max_length=60)] = None,
) -> Page[StockMovementOut]:
    await product_service.get_product(db, principal, product_id)  # 404 for an unknown or foreign product
    offset = decode_cursor(cursor)
    rows, total = await stock_service.list_movements(db, principal.tenant_id, product_id, limit=limit, offset=offset)
    return Page[StockMovementOut](
        items=[StockMovementOut.model_validate(r) for r in rows],
        total=total,
        next_cursor=next_cursor(offset, limit, total),
    )
