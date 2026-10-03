"""Customers (PRD F-009): lookup, create, edit, soft delete, and the balance each one owes.

Controllers stay thin and call this module. Rules enforced here: a phone is unique per tenant among live customers,
credit balances are hidden from staff, every change is audited (PRD §14.1).
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy import case, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import record_audit
from app.core.problems import Conflict, DomainError, NotFound
from app.core.tenancy import Principal
from app.models.customer import Customer
from app.models.payment import LedgerEntry
from app.models.tenant import TenantRole
from app.schemas.customer import CustomerCreate, CustomerOut, CustomerUpdate
from app.services import ledger_service

SORTS = ("name", "created_at", "balance")

_SIGNED = case((LedgerEntry.direction == "debit", LedgerEntry.amount), else_=-LedgerEntry.amount)


def _escape_like(text: str) -> str:
    return text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _out(customer: Customer, balance: Decimal, role: TenantRole) -> CustomerOut:
    out = CustomerOut.model_validate(customer)
    out.balance = None if role == TenantRole.staff else balance
    return out


async def lock_customer(db: AsyncSession, tenant_id: uuid.UUID, customer_id: uuid.UUID) -> Customer:
    """Load a live customer and lock the row, so two payments or sales on credit for one person queue up."""
    row = (
        await db.execute(
            select(Customer)
            .where(Customer.id == customer_id, Customer.tenant_id == tenant_id, Customer.deleted_at.is_(None))
            .with_for_update()
        )
    ).scalar_one_or_none()
    if row is None:
        raise NotFound("Customer")
    return row


async def get_live(db: AsyncSession, tenant_id: uuid.UUID, customer_id: uuid.UUID) -> Customer:
    row = (
        await db.execute(
            select(Customer).where(Customer.id == customer_id, Customer.tenant_id == tenant_id, Customer.deleted_at.is_(None))
        )
    ).scalar_one_or_none()
    if row is None:
        raise NotFound("Customer")
    return row


async def list_customers(
    db: AsyncSession,
    principal: Principal,
    *,
    q: str | None,
    owing_only: bool,
    sort: str,
    limit: int,
    offset: int,
) -> tuple[list[CustomerOut], int]:
    descending = sort.startswith("-")
    key = sort.lstrip("-")
    if key not in SORTS:
        raise DomainError(f"Cannot sort by '{key}'. Use one of: {', '.join(SORTS)}", code="invalid_sort", status_code=400)
    if (owing_only or key == "balance") and principal.role == TenantRole.staff:
        raise DomainError("Staff cannot see or filter by credit balances", code="forbidden_field", status_code=403)

    owed = (
        select(LedgerEntry.party_id.label("cid"), func.sum(_SIGNED).label("owed"))
        .where(LedgerEntry.tenant_id == principal.tenant_id, LedgerEntry.party_type == "customer")
        .group_by(LedgerEntry.party_id)
        .subquery()
    )
    balance_col = func.coalesce(owed.c.owed, 0)
    conditions: list[Any] = [Customer.tenant_id == principal.tenant_id, Customer.deleted_at.is_(None)]
    if q:
        like = f"%{_escape_like(q.strip())}%"
        conditions.append(or_(Customer.name.ilike(like, escape="\\"), Customer.phone.ilike(like, escape="\\")))
    if owing_only:
        conditions.append(balance_col > 0)
    base = select(Customer, balance_col.label("balance")).outerjoin(owed, owed.c.cid == Customer.id).where(*conditions)
    total = (await db.execute(select(func.count()).select_from(base.subquery()))).scalar_one()
    column: Any = {"name": func.lower(func.coalesce(Customer.name, "")), "created_at": Customer.created_at, "balance": balance_col}[key]
    order = (column.desc() if descending else column.asc(), Customer.id.asc())
    rows = (await db.execute(base.order_by(*order).limit(limit).offset(offset))).all()
    return [_out(c, Decimal(b).quantize(ledger_service.ZERO), principal.role) for c, b in rows], int(total)


async def get_customer(db: AsyncSession, principal: Principal, customer_id: uuid.UUID) -> CustomerOut:
    customer = await get_live(db, principal.tenant_id, customer_id)
    balance = await ledger_service.customer_balance(db, principal.tenant_id, customer.id)
    return _out(customer, balance, principal.role)


async def create_customer(db: AsyncSession, principal: Principal, body: CustomerCreate) -> CustomerOut:
    customer = Customer(
        tenant_id=principal.tenant_id, phone=body.phone, name=body.name, email=body.email, address=body.address
    )
    try:
        async with db.begin_nested():  # a duplicate phone must not poison the request transaction
            db.add(customer)
            await db.flush()
    except IntegrityError as exc:
        raise Conflict("A customer with this phone number already exists", code="duplicate_phone") from exc
    record_audit(
        db,
        "customer.created",
        tenant_id=principal.tenant_id,
        actor_id=principal.user_id,
        entity="customer",
        entity_id=customer.id,
    )
    await db.refresh(customer)
    return _out(customer, ledger_service.ZERO, principal.role)


async def update_customer(db: AsyncSession, principal: Principal, customer_id: uuid.UUID, body: CustomerUpdate) -> CustomerOut:
    customer = await get_live(db, principal.tenant_id, customer_id)
    changes = body.model_dump(exclude_unset=True)
    if not changes:
        raise DomainError("Nothing to update", code="empty_update")
    before = {k: getattr(customer, k) for k in changes}
    for field, value in changes.items():
        setattr(customer, field, value if field == "phone" else (value or None))
    try:
        async with db.begin_nested():
            await db.flush()
    except IntegrityError as exc:
        raise Conflict("A customer with this phone number already exists", code="duplicate_phone") from exc
    record_audit(
        db,
        "customer.updated",
        tenant_id=principal.tenant_id,
        actor_id=principal.user_id,
        entity="customer",
        entity_id=customer.id,
        before=before,
        after=changes,
    )
    await db.refresh(customer)
    balance = await ledger_service.customer_balance(db, principal.tenant_id, customer.id)
    return _out(customer, balance, principal.role)


async def delete_customer(db: AsyncSession, principal: Principal, customer_id: uuid.UUID) -> None:
    customer = await get_live(db, principal.tenant_id, customer_id)
    owed = await ledger_service.customer_balance(db, principal.tenant_id, customer.id)
    if owed > 0:
        raise DomainError(
            f"{customer.name or customer.phone} still owes {owed}. Record their payments before deleting them.",
            code="customer_owes_money",
        )
    customer.deleted_at = datetime.now(timezone.utc)
    await db.flush()
    record_audit(
        db,
        "customer.deleted",
        tenant_id=principal.tenant_id,
        actor_id=principal.user_id,
        entity="customer",
        entity_id=customer.id,
    )
