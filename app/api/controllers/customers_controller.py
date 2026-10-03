"""Customers and udhaar API (PRD F-009, §13.2): role gate -> tenant-scoped session -> service -> audit.

Staff can look customers up and add one while selling; the credit ledger and payments are for managers and owners, and
deleting a customer is owner-only (PRD §14.2).
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import ALL_ROLES, MANAGER_UP, OWNER_ONLY, get_tenant_db, require_role
from app.core.pagination import DEFAULT_LIMIT, MAX_LIMIT, Page, decode_cursor, next_cursor
from app.core.problems import NotFound
from app.core.tenancy import Principal
from app.schemas.customer import (
    CustomerCreate,
    CustomerOut,
    CustomerUpdate,
    LedgerEntryOut,
    PaymentCreate,
    PaymentOut,
)
from app.services import customer_service, ledger_service

router = APIRouter()

TenantDb = Annotated[AsyncSession, Depends(get_tenant_db, scope="function")]


def _id(raw: str) -> UUID:
    """A malformed id is a 404, the same answer as an unknown one (nothing to probe)."""
    try:
        return UUID(raw)
    except ValueError as exc:
        raise NotFound("Customer") from exc


@router.get("/", response_model=Page[CustomerOut])
async def list_customers(
    principal: Annotated[Principal, Depends(require_role(*ALL_ROLES))],
    db: TenantDb,
    q: Annotated[str | None, Query(max_length=80)] = None,
    owing_only: bool = False,
    sort: Annotated[str, Query(max_length=20)] = "name",
    limit: Annotated[int, Query(ge=1, le=MAX_LIMIT)] = DEFAULT_LIMIT,
    cursor: Annotated[str | None, Query(max_length=60)] = None,
) -> Page[CustomerOut]:
    offset = decode_cursor(cursor)
    items, total = await customer_service.list_customers(
        db, principal, q=q, owing_only=owing_only, sort=sort, limit=limit, offset=offset
    )
    return Page[CustomerOut](items=items, total=total, next_cursor=next_cursor(offset, limit, total))


@router.post("/", response_model=CustomerOut, status_code=status.HTTP_201_CREATED)
async def create_customer(
    body: CustomerCreate, principal: Annotated[Principal, Depends(require_role(*ALL_ROLES))], db: TenantDb
) -> CustomerOut:
    return await customer_service.create_customer(db, principal, body)


@router.get("/{customer_id}", response_model=CustomerOut)
async def get_customer(
    customer_id: str, principal: Annotated[Principal, Depends(require_role(*ALL_ROLES))], db: TenantDb
) -> CustomerOut:
    return await customer_service.get_customer(db, principal, _id(customer_id))


@router.patch("/{customer_id}", response_model=CustomerOut)
async def update_customer(
    customer_id: str,
    body: CustomerUpdate,
    principal: Annotated[Principal, Depends(require_role(*MANAGER_UP))],
    db: TenantDb,
) -> CustomerOut:
    return await customer_service.update_customer(db, principal, _id(customer_id), body)


@router.delete("/{customer_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_customer(
    customer_id: str, principal: Annotated[Principal, Depends(require_role(*OWNER_ONLY))], db: TenantDb
) -> Response:
    await customer_service.delete_customer(db, principal, _id(customer_id))
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{customer_id}/ledger", response_model=Page[LedgerEntryOut])
async def customer_ledger(
    customer_id: str,
    principal: Annotated[Principal, Depends(require_role(*MANAGER_UP))],
    db: TenantDb,
    limit: Annotated[int, Query(ge=1, le=MAX_LIMIT)] = DEFAULT_LIMIT,
    cursor: Annotated[str | None, Query(max_length=60)] = None,
) -> Page[LedgerEntryOut]:
    cid = _id(customer_id)
    await customer_service.get_live(db, principal.tenant_id, cid)
    offset = decode_cursor(cursor)
    rows, total = await ledger_service.list_entries(db, principal.tenant_id, cid, limit=limit, offset=offset)
    items = [
        LedgerEntryOut(
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
    return Page[LedgerEntryOut](items=items, total=total, next_cursor=next_cursor(offset, limit, total))


@router.post("/{customer_id}/payments", response_model=PaymentOut, status_code=status.HTTP_201_CREATED)
async def record_payment(
    customer_id: str,
    body: PaymentCreate,
    principal: Annotated[Principal, Depends(require_role(*MANAGER_UP))],
    db: TenantDb,
) -> PaymentOut:
    payment, balance = await ledger_service.record_customer_payment(
        db,
        tenant_id=principal.tenant_id,
        customer_id=_id(customer_id),
        amount=body.amount,
        method=body.method,
        user_id=principal.user_id,
    )
    return PaymentOut(
        id=payment.id,
        customer_id=payment.customer_id,
        amount=payment.amount,
        method=payment.method,
        created_at=payment.created_at,
        balance=balance,
    )
