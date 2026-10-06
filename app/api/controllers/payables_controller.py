"""Vendors and payables API (PRD F-012, R-005): role gate -> tenant-scoped session -> service -> audit.

Owners and managers run the vendor list, bills and payments; deleting a vendor and the payables report are owner-only.
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import MANAGER_UP, OWNER_ONLY, get_tenant_db, require_role
from app.core.pagination import DEFAULT_LIMIT, MAX_LIMIT, Page, decode_cursor, next_cursor
from app.core.tenancy import Principal
from app.schemas.payables import (
    PayableRow,
    ShopVendorCreate,
    ShopVendorOut,
    ShopVendorUpdate,
    VendorBillCreate,
    VendorBillOut,
    VendorLedgerEntryOut,
    VendorPaymentCreate,
    VendorPaymentOut,
)
from app.services import ledger_service, payables_service

router = APIRouter()

TenantDb = Annotated[AsyncSession, Depends(get_tenant_db, scope="function")]


@router.get("/", response_model=Page[ShopVendorOut])
async def list_vendors(
    principal: Annotated[Principal, Depends(require_role(*MANAGER_UP))],
    db: TenantDb,
    q: Annotated[str | None, Query(max_length=80)] = None,
    owing_only: bool = False,
    limit: Annotated[int, Query(ge=1, le=MAX_LIMIT)] = DEFAULT_LIMIT,
    cursor: Annotated[str | None, Query(max_length=60)] = None,
) -> Page[ShopVendorOut]:
    offset = decode_cursor(cursor)
    items, total = await payables_service.list_vendors(db, principal, q=q, owing_only=owing_only, limit=limit, offset=offset)
    return Page[ShopVendorOut](items=items, total=total, next_cursor=next_cursor(offset, limit, total))


@router.post("/", response_model=ShopVendorOut, status_code=status.HTTP_201_CREATED)
async def create_vendor(
    body: ShopVendorCreate, principal: Annotated[Principal, Depends(require_role(*MANAGER_UP))], db: TenantDb
) -> ShopVendorOut:
    return await payables_service.create_vendor(db, principal, body)


@router.get("/payables", response_model=list[PayableRow])
async def payables_report(
    principal: Annotated[Principal, Depends(require_role(*OWNER_ONLY))], db: TenantDb
) -> list[PayableRow]:
    """R-005. Declared before ``/{vendor_id}`` so ``payables`` is not read as an id."""
    return await payables_service.payables_report(db, principal)


@router.get("/{vendor_id}", response_model=ShopVendorOut)
async def get_vendor(
    vendor_id: UUID, principal: Annotated[Principal, Depends(require_role(*MANAGER_UP))], db: TenantDb
) -> ShopVendorOut:
    return await payables_service.get_vendor(db, principal, vendor_id)


@router.patch("/{vendor_id}", response_model=ShopVendorOut)
async def update_vendor(
    vendor_id: UUID,
    body: ShopVendorUpdate,
    principal: Annotated[Principal, Depends(require_role(*MANAGER_UP))],
    db: TenantDb,
) -> ShopVendorOut:
    return await payables_service.update_vendor(db, principal, vendor_id, body)


@router.delete("/{vendor_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_vendor(
    vendor_id: UUID, principal: Annotated[Principal, Depends(require_role(*OWNER_ONLY))], db: TenantDb
) -> Response:
    await payables_service.delete_vendor(db, principal, vendor_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{vendor_id}/bills", response_model=VendorBillOut, status_code=status.HTTP_201_CREATED)
async def add_bill(
    vendor_id: UUID,
    body: VendorBillCreate,
    principal: Annotated[Principal, Depends(require_role(*MANAGER_UP))],
    db: TenantDb,
) -> VendorBillOut:
    return await payables_service.add_bill(db, principal, vendor_id, body)


@router.post("/{vendor_id}/payments", response_model=VendorPaymentOut, status_code=status.HTTP_201_CREATED)
async def pay_vendor(
    vendor_id: UUID,
    body: VendorPaymentCreate,
    principal: Annotated[Principal, Depends(require_role(*MANAGER_UP))],
    db: TenantDb,
) -> VendorPaymentOut:
    return await payables_service.pay_vendor(db, principal, vendor_id, body)


@router.get("/{vendor_id}/ledger", response_model=Page[VendorLedgerEntryOut])
async def vendor_ledger(
    vendor_id: UUID,
    principal: Annotated[Principal, Depends(require_role(*MANAGER_UP))],
    db: TenantDb,
    limit: Annotated[int, Query(ge=1, le=MAX_LIMIT)] = DEFAULT_LIMIT,
    cursor: Annotated[str | None, Query(max_length=60)] = None,
) -> Page[VendorLedgerEntryOut]:
    await payables_service.get_live(db, principal.tenant_id, vendor_id)
    offset = decode_cursor(cursor)
    rows, total = await ledger_service.list_entries(
        db, principal.tenant_id, vendor_id, limit=limit, offset=offset, party_type=payables_service.PARTY
    )
    items = [
        VendorLedgerEntryOut(
            id=e.id,
            direction=e.direction,  # type: ignore[arg-type]
            amount=e.amount,
            ref_type=e.ref_type,
            ref_id=e.ref_id,
            created_at=e.created_at,
            balance_after=after,
        )
        for e, after in rows
    ]
    return Page[VendorLedgerEntryOut](items=items, total=total, next_cursor=next_cursor(offset, limit, total))
