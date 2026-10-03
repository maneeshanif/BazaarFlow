"""The home dashboard (PRD F-004, D-001): one call returns every figure for the signed-in role.

The numbers come from ``report_service``, the same code the agent's reporting tools use, so a figure said in chat is
the figure on the screen. Staff get sales, orders and low stock; profit, udhaar, approvals and the briefing are for
owners and managers. The briefing is written from the figures by a fixed template: it costs nothing and can always
be checked against the cards above it.
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.tenancy import Principal
from app.models.order import Order
from app.models.tenant import TenantRole
from app.schemas.dashboard import CountFigure, DashboardOut, DashboardRange, MoneyFigure, ProfitFigure, TrendDay
from app.services import ledger_service, report_service
from app.services.report_service import SHOP_TZ

ZERO = Decimal("0.00")
DAYS = {"today": 1, "7d": 7, "30d": 30}


def bounds(range_: DashboardRange, now: datetime | None = None) -> tuple[tuple[datetime, datetime], tuple[datetime, datetime]]:
    """UTC (start, end) of the range and of the equal-length range just before it, by the shop's local days."""
    local = (now or datetime.now(timezone.utc)).astimezone(SHOP_TZ)
    midnight = datetime.combine(local.date(), time.min, tzinfo=SHOP_TZ)
    days = DAYS[range_]
    end = midnight + timedelta(days=1)
    start = end - timedelta(days=days)
    previous_start = start - timedelta(days=days)
    utc = timezone.utc
    return (start.astimezone(utc), end.astimezone(utc)), (previous_start.astimezone(utc), start.astimezone(utc))


def _change(value: Decimal | int, previous: Decimal | int) -> int | None:
    if not previous:
        return None
    return int(round((Decimal(value) - Decimal(previous)) * 100 / Decimal(previous)))


def _rs(value: Decimal) -> str:
    return f"Rs {value:,.0f}"


async def _trend(db: AsyncSession, principal: Principal, now: datetime | None) -> list[TrendDay]:
    (start, end), _ = bounds("7d", now)
    local_day = func.date(func.timezone("Asia/Karachi", Order.created_at))
    rows = (
        await db.execute(
            select(local_day, func.coalesce(func.sum(Order.total), 0), func.count(Order.id))
            .where(Order.tenant_id == principal.tenant_id, Order.status == "posted", Order.created_at >= start, Order.created_at < end)
            .group_by(local_day)
        )
    ).all()
    found: dict[date, tuple[Decimal, int]] = {d: (Decimal(t), int(n)) for d, t, n in rows}
    first = start.astimezone(SHOP_TZ).date()
    days = [first + timedelta(days=i) for i in range(7)]
    return [TrendDay(day=d, total=found.get(d, (ZERO, 0))[0].quantize(ZERO), orders=found.get(d, (ZERO, 0))[1]) for d in days]


def _briefing(
    *, range_: DashboardRange, sales: MoneyFigure, orders: CountFigure, low_stock: int, debtor: tuple[str, Decimal] | None, approvals: int, owed: Decimal
) -> str:
    when = {"today": "Today", "7d": "In the last 7 days", "30d": "In the last 30 days"}[range_]
    if orders.value == 0:
        parts = [f"{when} there are no sales yet."]
    else:
        trend = ""
        if sales.change_percent is not None:
            trend = f", {'up' if sales.change_percent >= 0 else 'down'} {abs(sales.change_percent)}% on the period before"
        parts = [f"{when} you made {_rs(sales.value)} from {orders.value} {'order' if orders.value == 1 else 'orders'}{trend}."]
    if low_stock:
        parts.append(f"{low_stock} {'item is' if low_stock == 1 else 'items are'} low on stock.")
    if debtor is not None:
        parts.append(f"Customers owe {_rs(owed)} in total; {debtor[0]} owes the most, {_rs(debtor[1])}.")
    if approvals:
        parts.append(f"{approvals} {'request is' if approvals == 1 else 'requests are'} waiting for your approval.")
    if len(parts) == 1 and orders.value > 0:
        parts.append("Nothing needs your attention.")
    return " ".join(parts)


async def summary(db: AsyncSession, principal: Principal, range_: DashboardRange, *, now: datetime | None = None) -> DashboardOut:
    tenant = principal.tenant_id
    (start, end), (prev_start, prev_end) = bounds(range_, now)
    now_utc = now or datetime.now(timezone.utc)

    current = await report_service.sales_summary(db, tenant, start, end)
    before = await report_service.sales_summary(db, tenant, prev_start, prev_end)
    sales = MoneyFigure(value=current.total, previous=before.total, change_percent=_change(current.total, before.total))
    orders = CountFigure(value=current.orders, previous=before.orders, change_percent=_change(current.orders, before.orders))
    low_stock = await report_service.low_stock_count(db, tenant)
    trend = await _trend(db, principal, now)

    privileged = principal.role in (TenantRole.owner, TenantRole.manager)
    profit = owed = approvals = briefing = None
    if privileged:
        now_profit = await report_service.profit(db, tenant, start, end)
        before_profit = await report_service.profit(db, tenant, prev_start, prev_end)
        profit = ProfitFigure(
            value=now_profit.profit,
            previous=before_profit.profit,
            change_percent=_change(now_profit.profit, before_profit.profit),
            orders_without_cost=now_profit.orders_without_cost,
        )
        owed = await report_service.unpaid_udhaar(db, tenant)
        approvals = await report_service.approvals_waiting(db, tenant)
        debtor = await ledger_service.top_debtor(db, tenant)
        briefing = _briefing(range_=range_, sales=sales, orders=orders, low_stock=low_stock, debtor=debtor, approvals=approvals, owed=owed)

    return DashboardOut(
        role=principal.role.value if hasattr(principal.role, "value") else str(principal.role),
        range=range_,
        sales=sales,
        orders=orders,
        low_stock=low_stock,
        profit=profit,
        unpaid_udhaar=owed,
        approvals_waiting=approvals,
        briefing=briefing,
        trend=trend,
        generated_at=now_utc,
    )
