"""Vendors and payables (PRD F-012, R-005): vendors, purchase bills, payments, and what the shop owes.

What is owed to a vendor is the sum of its ``ledger_entries`` (debit = a bill, credit = a payment), the same
append-only ledger the customer udhaar uses, so the balance always reconciles to the entries behind it. Payments are
applied to the oldest bills first when the report works out what is overdue.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import record_audit
from app.core.problems import DomainError, NotFound
from app.core.search import escape_like
from app.core.tenancy import Principal
from app.models.vendor import Vendor, VendorBill, VendorPayment
from app.schemas.payables import (
    PayableRow,
    ShopVendorCreate,
    ShopVendorOut,
    ShopVendorUpdate,
    VendorBillCreate,
    VendorBillOut,
    VendorPaymentCreate,
    VendorPaymentOut,
)
from app.services import ledger_service

ZERO = ledger_service.ZERO
PARTY = "vendor"


def _out(vendor: Vendor, balance: Decimal) -> ShopVendorOut:
    out = ShopVendorOut.model_validate(vendor)
    out.balance = balance
    return out


async def get_live(db: AsyncSession, tenant_id: uuid.UUID, vendor_id: uuid.UUID, *, lock: bool = False) -> Vendor:
    stmt = select(Vendor).where(Vendor.id == vendor_id, Vendor.tenant_id == tenant_id, Vendor.deleted_at.is_(None))
    if lock:
        stmt = stmt.with_for_update()  # two payments to one vendor queue up instead of racing
    row = (await db.execute(stmt)).scalar_one_or_none()
    if row is None:
        raise NotFound("Vendor")
    return row


async def balance_of(db: AsyncSession, tenant_id: uuid.UUID, vendor_id: uuid.UUID) -> Decimal:
    return (await ledger_service.balances(db, tenant_id, [vendor_id], party_type=PARTY))[vendor_id]


async def list_vendors(
    db: AsyncSession, principal: Principal, *, q: str | None, owing_only: bool, limit: int, offset: int
) -> tuple[list[ShopVendorOut], int]:
    conditions: list[Any] = [Vendor.tenant_id == principal.tenant_id, Vendor.deleted_at.is_(None)]
    if q:
        like = f"%{escape_like(q.strip())}%"
        conditions.append(or_(Vendor.name.ilike(like, escape="\\"), Vendor.phone.ilike(like, escape="\\")))
    rows = (await db.execute(select(Vendor).where(*conditions).order_by(func.lower(Vendor.name), Vendor.id))).scalars().all()
    balances = await ledger_service.balances(db, principal.tenant_id, [v.id for v in rows], party_type=PARTY)
    items = [_out(v, balances[v.id]) for v in rows if not owing_only or balances[v.id] > 0]
    return items[offset : offset + limit], len(items)


async def get_vendor(db: AsyncSession, principal: Principal, vendor_id: uuid.UUID) -> ShopVendorOut:
    vendor = await get_live(db, principal.tenant_id, vendor_id)
    return _out(vendor, await balance_of(db, principal.tenant_id, vendor.id))


async def create_vendor(db: AsyncSession, principal: Principal, body: ShopVendorCreate) -> ShopVendorOut:
    vendor = Vendor(tenant_id=principal.tenant_id, name=body.name, phone=body.phone, balance=ZERO)
    db.add(vendor)
    await db.flush()
    record_audit(
        db, "vendor.created", tenant_id=principal.tenant_id, actor_id=principal.user_id, entity="vendor", entity_id=vendor.id
    )
    await db.refresh(vendor)
    return _out(vendor, ZERO)


async def update_vendor(db: AsyncSession, principal: Principal, vendor_id: uuid.UUID, body: ShopVendorUpdate) -> ShopVendorOut:
    vendor = await get_live(db, principal.tenant_id, vendor_id)
    changes = body.model_dump(exclude_unset=True)
    if not changes:
        raise DomainError("Nothing to update", code="empty_update")
    if "name" in changes and changes["name"] is None:
        raise DomainError("A vendor needs a name", code="name_required")
    before = {k: getattr(vendor, k) for k in changes}
    for field, value in changes.items():
        setattr(vendor, field, value)
    await db.flush()
    record_audit(
        db,
        "vendor.updated",
        tenant_id=principal.tenant_id,
        actor_id=principal.user_id,
        entity="vendor",
        entity_id=vendor.id,
        before=before,
        after=changes,
    )
    await db.refresh(vendor)
    return _out(vendor, await balance_of(db, principal.tenant_id, vendor.id))


async def delete_vendor(db: AsyncSession, principal: Principal, vendor_id: uuid.UUID) -> None:
    vendor = await get_live(db, principal.tenant_id, vendor_id)
    owed = await balance_of(db, principal.tenant_id, vendor.id)
    if owed != 0:
        raise DomainError(
            f"You still owe {vendor.name} {owed}. Record the payment before deleting this vendor.",
            code="vendor_has_balance",
        )
    vendor.deleted_at = datetime.now(timezone.utc)
    await db.flush()
    record_audit(
        db, "vendor.deleted", tenant_id=principal.tenant_id, actor_id=principal.user_id, entity="vendor", entity_id=vendor.id
    )


async def add_bill(db: AsyncSession, principal: Principal, vendor_id: uuid.UUID, body: VendorBillCreate) -> VendorBillOut:
    vendor = await get_live(db, principal.tenant_id, vendor_id, lock=True)
    bill = VendorBill(
        tenant_id=principal.tenant_id,
        vendor_id=vendor.id,
        amount=body.amount,
        due_date=body.due_date,
        reference=body.reference,
        note=body.note,
        created_by=principal.user_id,
    )
    db.add(bill)
    await db.flush()
    await ledger_service.add_entry(
        db,
        tenant_id=principal.tenant_id,
        party_type=PARTY,
        party_id=vendor.id,
        amount=body.amount,
        direction="debit",
        ref_type="vendor_bill",
        ref_id=bill.id,
        created_by=principal.user_id,
    )
    balance = await balance_of(db, principal.tenant_id, vendor.id)
    record_audit(
        db,
        "vendor.bill_added",
        tenant_id=principal.tenant_id,
        actor_id=principal.user_id,
        entity="vendor",
        entity_id=vendor.id,
        after={"bill_id": str(bill.id), "amount": str(body.amount), "balance_after": str(balance)},
    )
    await db.refresh(bill)
    out = VendorBillOut.model_validate({**{c: getattr(bill, c) for c in ("id", "vendor_id", "amount", "due_date", "reference", "note", "created_at")}, "balance": balance})
    return out


async def pay_vendor(
    db: AsyncSession, principal: Principal, vendor_id: uuid.UUID, body: VendorPaymentCreate
) -> VendorPaymentOut:
    """The shop pays a vendor. Refused when it is more than is owed, so the ledger never goes negative."""
    vendor = await get_live(db, principal.tenant_id, vendor_id, lock=True)
    owed = await balance_of(db, principal.tenant_id, vendor.id)
    if body.amount > owed:
        raise DomainError(f"That is more than you owe. The balance is {owed}.", code="payment_exceeds_balance")
    payment = VendorPayment(
        tenant_id=principal.tenant_id, vendor_id=vendor.id, amount=body.amount, method=body.method, created_by=principal.user_id
    )
    db.add(payment)
    await db.flush()
    await ledger_service.add_entry(
        db,
        tenant_id=principal.tenant_id,
        party_type=PARTY,
        party_id=vendor.id,
        amount=body.amount,
        direction="credit",
        ref_type="vendor_payment",
        ref_id=payment.id,
        created_by=principal.user_id,
    )
    record_audit(
        db,
        "vendor.paid",
        tenant_id=principal.tenant_id,
        actor_id=principal.user_id,
        entity="vendor",
        entity_id=vendor.id,
        after={
            "payment_id": str(payment.id),
            "amount": str(body.amount),
            "method": body.method,
            "balance_after": str(owed - body.amount),
        },
    )
    await db.refresh(payment)
    return VendorPaymentOut.model_validate(
        {
            **{c: getattr(payment, c) for c in ("id", "vendor_id", "amount", "method", "created_at")},
            "balance": owed - body.amount,
        }
    )


async def payables_report(db: AsyncSession, principal: Principal, *, today: date | None = None) -> list[PayableRow]:
    """What the shop owes each vendor, how much is overdue and the next due date (R-005). Vendors owed nothing are left out."""
    today = today or datetime.now(timezone.utc).date()
    vendors = (
        await db.execute(
            select(Vendor)
            .where(Vendor.tenant_id == principal.tenant_id, Vendor.deleted_at.is_(None))
            .order_by(func.lower(Vendor.name), Vendor.id)
        )
    ).scalars().all()
    balances = await ledger_service.balances(db, principal.tenant_id, [v.id for v in vendors], party_type=PARTY)
    owing = [v for v in vendors if balances[v.id] > 0]
    if not owing:
        return []
    ids = [v.id for v in owing]
    bills = (
        await db.execute(
            select(VendorBill)
            .where(VendorBill.tenant_id == principal.tenant_id, VendorBill.vendor_id.in_(ids))
            .order_by(VendorBill.created_at, VendorBill.id)
        )
    ).scalars().all()
    paid = {
        vendor_id: Decimal(total)
        for vendor_id, total in (
            await db.execute(
                select(VendorPayment.vendor_id, func.sum(VendorPayment.amount))
                .where(VendorPayment.tenant_id == principal.tenant_id, VendorPayment.vendor_id.in_(ids))
                .group_by(VendorPayment.vendor_id)
            )
        ).all()
    }
    by_vendor: dict[uuid.UUID, list[VendorBill]] = {}
    for bill in bills:
        by_vendor.setdefault(bill.vendor_id, []).append(bill)
    rows: list[PayableRow] = []
    for vendor in owing:
        remaining_payment = paid.get(vendor.id, ZERO)
        overdue = ZERO
        next_due: date | None = None
        for bill in by_vendor.get(vendor.id, []):
            applied = min(bill.amount, remaining_payment)  # payments clear the oldest bills first
            remaining_payment -= applied
            unpaid = bill.amount - applied
            if unpaid <= 0 or bill.due_date is None:
                continue
            if bill.due_date < today:
                overdue += unpaid
            if next_due is None or bill.due_date < next_due:
                next_due = bill.due_date
        rows.append(
            PayableRow(
                vendor_id=vendor.id,
                name=vendor.name,
                phone=vendor.phone,
                owed=balances[vendor.id],
                overdue=overdue.quantize(ZERO),
                next_due=next_due,
            )
        )
    return rows
