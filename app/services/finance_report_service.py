"""Finance overview, cash book and the finance dashboard (PRD F-013, D-002, R-004, R-005).

The figures reuse ``report_service`` (revenue, profit) and ``payables_service`` (what the shop owes vendors), so a number
here is the number the dashboard, the agent and the reports quote. Money is Decimal throughout; days follow the shop's
timezone. Receivables are aged first-in-first-out: a customer's payments clear their oldest credit sales first, so what
remains is aged by how long the oldest unpaid sale has waited.

Owners see everything. A manager sees revenue, the cash/credit split and receivables; gross margin and vendor payables
are for the owner (staff cannot open any of it).
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import case, func, literal, select, union_all
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.tenancy import Principal
from app.models.order import Order
from app.models.payment import LedgerEntry, Payment
from app.models.tenant import TenantRole
from app.models.vendor import VendorPayment
from app.schemas.dashboard import DashboardRange, MoneyFigure
from app.schemas.finance import (
    AgingBucket,
    CashBookEntry,
    CashCreditSplit,
    FinanceOverview,
    FinanceTrendDay,
    GrossMargin,
    Payables,
    Receivables,
)
from app.services import payables_service, report_service
from app.services.dashboard_service import _change, bounds
from app.services.report_service import SHOP_TZ

ZERO = Decimal("0.00")
BUCKETS: tuple[tuple[str, int, int | None], ...] = (
    ("0 to 7 days", 0, 7),
    ("8 to 14 days", 8, 14),
    ("15 to 30 days", 15, 30),
    ("Over 30 days", 31, None),
)


def _trend_days(range_: DashboardRange) -> int:
    return 30 if range_ == "30d" else 7


async def _trend(db: AsyncSession, tenant_id: uuid.UUID, days: int, now: datetime) -> list[FinanceTrendDay]:
    local_today = now.astimezone(SHOP_TZ).date()
    first = local_today - timedelta(days=days - 1)
    start = datetime.combine(first, datetime.min.time(), tzinfo=SHOP_TZ).astimezone(timezone.utc)
    end = datetime.combine(local_today + timedelta(days=1), datetime.min.time(), tzinfo=SHOP_TZ).astimezone(timezone.utc)
    local_day = func.date(func.timezone("Asia/Karachi", Order.created_at))
    rows = (
        await db.execute(
            select(local_day, func.coalesce(func.sum(Order.total), 0), func.count(Order.id))
            .where(Order.tenant_id == tenant_id, Order.status == "posted", Order.created_at >= start, Order.created_at < end)
            .group_by(local_day)
        )
    ).all()
    found: dict[date, tuple[Decimal, int]] = {d: (Decimal(t), int(n)) for d, t, n in rows}
    out = []
    for offset in range(days):
        day = first + timedelta(days=offset)
        revenue, orders = found.get(day, (ZERO, 0))
        out.append(FinanceTrendDay(day=day, revenue=revenue.quantize(ZERO), orders=orders))
    return out


async def _split(db: AsyncSession, tenant_id: uuid.UUID, start: datetime, end: datetime, revenue: Decimal) -> CashCreditSplit:
    credit = (
        await db.execute(
            select(func.coalesce(func.sum(LedgerEntry.amount), 0))
            .join(Order, Order.id == LedgerEntry.ref_id)
            .where(
                LedgerEntry.tenant_id == tenant_id,
                LedgerEntry.party_type == "customer",
                LedgerEntry.direction == "debit",
                LedgerEntry.ref_type == "order",
                Order.tenant_id == tenant_id,
                Order.status == "posted",
                Order.created_at >= start,
                Order.created_at < end,
            )
        )
    ).scalar_one()
    on_credit = Decimal(credit).quantize(ZERO)
    paid = (revenue - on_credit).quantize(ZERO)
    percent = int(round(on_credit * 100 / revenue)) if revenue > 0 else None
    return CashCreditSplit(paid_now=paid, on_credit=on_credit, credit_percent=percent)


async def receivables(db: AsyncSession, tenant_id: uuid.UUID, now: datetime) -> Receivables:
    """What customers owe, aged first-in-first-out by how long the oldest unpaid credit sale has waited (R-004)."""
    credits = {
        party: Decimal(total)
        for party, total in (
            await db.execute(
                select(LedgerEntry.party_id, func.sum(LedgerEntry.amount)).where(
                    LedgerEntry.tenant_id == tenant_id, LedgerEntry.party_type == "customer", LedgerEntry.direction == "credit"
                ).group_by(LedgerEntry.party_id)
            )
        ).all()
    }
    debits = (
        await db.execute(
            select(LedgerEntry.party_id, LedgerEntry.amount, LedgerEntry.created_at)
            .where(LedgerEntry.tenant_id == tenant_id, LedgerEntry.party_type == "customer", LedgerEntry.direction == "debit")
            .order_by(LedgerEntry.created_at, LedgerEntry.id)
        )
    ).all()
    today = now.astimezone(SHOP_TZ).date()
    amounts = [ZERO] * len(BUCKETS)
    customers: list[set[uuid.UUID]] = [set() for _ in BUCKETS]
    remaining = dict(credits)
    for party, amount, created_at in debits:
        pay_down = min(Decimal(amount), remaining.get(party, ZERO))
        remaining[party] = remaining.get(party, ZERO) - pay_down
        unpaid = Decimal(amount) - pay_down
        if unpaid <= 0:
            continue
        age = (today - created_at.astimezone(SHOP_TZ).date()).days
        for index, (_label, low, high) in enumerate(BUCKETS):
            if age >= low and (high is None or age <= high):
                amounts[index] += unpaid
                customers[index].add(party)
                break
    buckets = [
        AgingBucket(label=label, amount=amounts[i].quantize(ZERO), customers=len(customers[i]))
        for i, (label, _low, _high) in enumerate(BUCKETS)
    ]
    return Receivables(total=sum(amounts, ZERO).quantize(ZERO), buckets=buckets)


async def overview(db: AsyncSession, principal: Principal, range_: DashboardRange, *, now: datetime | None = None) -> FinanceOverview:
    tenant = principal.tenant_id
    now_utc = now or datetime.now(timezone.utc)
    (start, end), (prev_start, prev_end) = bounds(range_, now_utc)
    current = await report_service.sales_summary(db, tenant, start, end)
    before = await report_service.sales_summary(db, tenant, prev_start, prev_end)
    revenue = MoneyFigure(value=current.total, previous=before.total, change_percent=_change(current.total, before.total))
    owed = await receivables(db, tenant, now_utc)

    margin: GrossMargin | None = None
    payables: Payables | None = None
    if principal.role == TenantRole.owner:
        summary = await report_service.profit(db, tenant, start, end)
        percent = int(round(summary.profit * 100 / summary.revenue)) if summary.revenue > 0 else None
        margin = GrossMargin(
            margin_percent=percent,
            profit=summary.profit,
            revenue_counted=summary.revenue,
            orders_without_cost=summary.orders_without_cost,
        )
        rows = await payables_service.payables_report(db, principal)
        payables = Payables(
            total=sum((r.owed for r in rows), ZERO).quantize(ZERO),
            overdue=sum((r.overdue for r in rows), ZERO).quantize(ZERO),
            vendors=len(rows),
        )

    ever_sold = (await db.execute(select(func.count()).select_from(Order).where(Order.tenant_id == tenant, Order.status == "posted"))).scalar_one()
    is_empty = ever_sold == 0 and owed.total == 0 and (payables is None or payables.total == 0)
    return FinanceOverview(
        role=principal.role.value,
        range=range_,
        revenue=revenue,
        trend=await _trend(db, tenant, _trend_days(range_), now_utc),
        split=await _split(db, tenant, start, end, current.total),
        receivables=owed,
        gross_margin=margin,
        payables=payables,
        is_empty=is_empty,
        generated_at=now_utc,
    )


async def cash_book(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    *,
    direction: str | None,
    since: datetime | None,
    until: datetime | None,
    limit: int,
    offset: int,
) -> tuple[list[CashBookEntry], int]:
    """Money in (payments received) and money out (payments to vendors), newest first (F-013 ledger)."""
    received = select(
        Payment.id.label("id"),
        Payment.created_at.label("created_at"),
        literal("in").label("direction"),
        case((Payment.order_id.is_(None), "udhaar_payment"), else_="sale_payment").label("kind"),
        Payment.amount.label("amount"),
        Payment.method.label("method"),
        Payment.customer_id.label("party_id"),
    ).where(Payment.tenant_id == tenant_id, Payment.status == "completed")
    paid_out = select(
        VendorPayment.id.label("id"),
        VendorPayment.created_at.label("created_at"),
        literal("out").label("direction"),
        literal("vendor_payment").label("kind"),
        VendorPayment.amount.label("amount"),
        VendorPayment.method.label("method"),
        VendorPayment.vendor_id.label("party_id"),
    ).where(VendorPayment.tenant_id == tenant_id)
    book = union_all(received, paid_out).subquery()
    conditions = []
    if direction is not None:
        conditions.append(book.c.direction == direction)
    if since is not None:
        conditions.append(book.c.created_at >= since)
    if until is not None:
        conditions.append(book.c.created_at < until)
    total = (await db.execute(select(func.count()).select_from(book).where(*conditions))).scalar_one()
    rows = (
        await db.execute(
            select(book).where(*conditions).order_by(book.c.created_at.desc(), book.c.id.desc()).limit(limit).offset(offset)
        )
    ).all()
    items = [
        CashBookEntry(
            id=r.id,
            created_at=r.created_at,
            direction=r.direction,
            kind=r.kind,
            amount=Decimal(r.amount).quantize(ZERO),
            method=r.method,
            party_id=r.party_id,
        )
        for r in rows
    ]
    return items, int(total)
