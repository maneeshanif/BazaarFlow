"""The udhaar (customer credit) ledger (PRD F-009, §12.3).

An append-only list of debits (the customer owes more: a sale on credit) and credits (they paid). A customer's balance is
the sum of debits minus the sum of credits, so it always reconciles to the entries that produced it.
"""

from __future__ import annotations

import uuid
from decimal import Decimal

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import record_audit
from app.core.problems import DomainError
from app.models.payment import LedgerEntry, Payment

ZERO = Decimal("0.00")

_SIGNED = case((LedgerEntry.direction == "debit", LedgerEntry.amount), else_=-LedgerEntry.amount)


async def add_entry(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    party_type: str,
    party_id: uuid.UUID,
    amount: Decimal,
    direction: str,
    ref_type: str | None,
    ref_id: uuid.UUID | None,
    created_by: uuid.UUID | None,
) -> LedgerEntry:
    entry = LedgerEntry(
        tenant_id=tenant_id,
        party_type=party_type,
        party_id=party_id,
        amount=amount,
        direction=direction,
        ref_type=ref_type,
        ref_id=ref_id,
        created_by=created_by,
    )
    db.add(entry)
    await db.flush()
    return entry


async def balances(db: AsyncSession, tenant_id: uuid.UUID, customer_ids: list[uuid.UUID]) -> dict[uuid.UUID, Decimal]:
    """What each customer owes (customers with no entries owe zero)."""
    if not customer_ids:
        return {}
    rows = (
        await db.execute(
            select(LedgerEntry.party_id, func.coalesce(func.sum(_SIGNED), 0))
            .where(
                LedgerEntry.tenant_id == tenant_id,
                LedgerEntry.party_type == "customer",
                LedgerEntry.party_id.in_(customer_ids),
            )
            .group_by(LedgerEntry.party_id)
        )
    ).all()
    found = {party: Decimal(total).quantize(ZERO) for party, total in rows}
    return {cid: found.get(cid, ZERO) for cid in customer_ids}


async def customer_balance(db: AsyncSession, tenant_id: uuid.UUID, customer_id: uuid.UUID) -> Decimal:
    return (await balances(db, tenant_id, [customer_id]))[customer_id]


async def total_outstanding(db: AsyncSession, tenant_id: uuid.UUID) -> Decimal:
    """Everything customers owe the shop (the dashboard's "Unpaid udhaar")."""
    per_customer = (
        select(func.sum(_SIGNED).label("owed"))
        .where(LedgerEntry.tenant_id == tenant_id, LedgerEntry.party_type == "customer")
        .group_by(LedgerEntry.party_id)
        .subquery()
    )
    total = (await db.execute(select(func.coalesce(func.sum(per_customer.c.owed), 0)).where(per_customer.c.owed > 0))).scalar_one()
    return Decimal(total).quantize(ZERO)


async def list_entries(
    db: AsyncSession, tenant_id: uuid.UUID, customer_id: uuid.UUID, *, limit: int, offset: int
) -> tuple[list[tuple[LedgerEntry, Decimal]], int]:
    """Entries newest first, each with the running balance after it (computed oldest first so it always adds up)."""
    running = func.sum(_SIGNED).over(order_by=(LedgerEntry.created_at, LedgerEntry.id))
    inner = (
        select(LedgerEntry, running.label("balance_after"))
        .where(
            LedgerEntry.tenant_id == tenant_id,
            LedgerEntry.party_type == "customer",
            LedgerEntry.party_id == customer_id,
        )
        .subquery()
    )
    total = (await db.execute(select(func.count()).select_from(inner))).scalar_one()
    from sqlalchemy.orm import aliased

    entry = aliased(LedgerEntry, inner)
    rows = (
        await db.execute(
            select(entry, inner.c.balance_after)
            .order_by(inner.c.created_at.desc(), inner.c.id.desc())
            .limit(limit)
            .offset(offset)
        )
    ).all()
    return [(e, Decimal(b).quantize(ZERO)) for e, b in rows], int(total)


async def record_customer_payment(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    customer_id: uuid.UUID,
    amount: Decimal,
    method: str,
    user_id: uuid.UUID,
) -> tuple[Payment, Decimal]:
    """A customer pays down their udhaar. Refused when it is more than they owe, so the ledger never goes negative."""
    from app.services.customer_service import lock_customer

    await lock_customer(db, tenant_id, customer_id)  # two payments for one customer queue up instead of racing
    owed = await customer_balance(db, tenant_id, customer_id)
    if amount > owed:
        raise DomainError(
            f"That is more than they owe. The balance is {owed}.",
            code="payment_exceeds_balance",
        )
    payment = Payment(
        tenant_id=tenant_id, customer_id=customer_id, order_id=None, amount=amount, method=method, created_by=user_id
    )
    db.add(payment)
    await db.flush()
    await add_entry(
        db,
        tenant_id=tenant_id,
        party_type="customer",
        party_id=customer_id,
        amount=amount,
        direction="credit",
        ref_type="payment",
        ref_id=payment.id,
        created_by=user_id,
    )
    record_audit(
        db,
        "payment.recorded",
        tenant_id=tenant_id,
        actor_id=user_id,
        entity="customer",
        entity_id=customer_id,
        after={"amount": str(amount), "method": method, "balance_after": str(owed - amount), "payment_id": str(payment.id)},
    )
    return payment, owed - amount
