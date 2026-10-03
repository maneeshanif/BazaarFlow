"""Figures a shopkeeper asks for (PRD F-004, D-001, §36.4): sales, profit, low stock, udhaar, approvals waiting.

One implementation serves the dashboard and the agent's reporting tools, so a number said in chat is the number on the
screen. Money is Decimal throughout. Days follow the shop's timezone (Asia/Karachi) and are compared in UTC.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, time, timedelta, timezone
from decimal import ROUND_HALF_UP, Decimal
from zoneinfo import ZoneInfo

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent import ActionStatus, AgentAction
from app.models.inventory import InventoryItem
from app.models.order import Order, OrderItem
from app.models.product import Product
from app.services import ledger_service

SHOP_TZ = ZoneInfo("Asia/Karachi")
CENT = Decimal("0.01")
PERIODS = ("today", "week", "month")


def _money(value: Decimal | int | float) -> Decimal:
    return Decimal(value).quantize(CENT, rounding=ROUND_HALF_UP)


def period_bounds(period: str, now: datetime | None = None) -> tuple[datetime, datetime]:
    """UTC start (inclusive) and end (exclusive) of today, the last 7 days including today, or the calendar month."""
    local = (now or datetime.now(timezone.utc)).astimezone(SHOP_TZ)
    midnight = datetime.combine(local.date(), time.min, tzinfo=SHOP_TZ)
    if period == "today":
        start = midnight
    elif period == "week":
        start = midnight - timedelta(days=6)
    elif period == "month":
        start = midnight.replace(day=1)
    else:
        raise ValueError(f"period must be one of {PERIODS}")
    return start.astimezone(timezone.utc), (midnight + timedelta(days=1)).astimezone(timezone.utc)


@dataclass(frozen=True)
class SalesSummary:
    orders: int
    total: Decimal


@dataclass(frozen=True)
class ProfitSummary:
    profit: Decimal
    orders_counted: int
    orders_without_cost: int  # left out: a line has no cost, so its profit cannot be known


def _in_range(tenant_id: uuid.UUID, start: datetime, end: datetime) -> list[object]:
    return [Order.tenant_id == tenant_id, Order.status == "posted", Order.created_at >= start, Order.created_at < end]


async def sales_summary(db: AsyncSession, tenant_id: uuid.UUID, start: datetime, end: datetime) -> SalesSummary:
    count, total = (
        await db.execute(select(func.count(Order.id), func.coalesce(func.sum(Order.total), 0)).where(*_in_range(tenant_id, start, end)))  # type: ignore[arg-type]
    ).one()
    return SalesSummary(orders=int(count), total=_money(Decimal(total)))


async def profit(db: AsyncSession, tenant_id: uuid.UUID, start: datetime, end: datetime) -> ProfitSummary:
    """Order total minus the cost of its lines, for orders whose every line has a cost."""
    rows = (
        await db.execute(
            select(
                Order.id,
                Order.total,
                func.sum(OrderItem.unit_cost * OrderItem.qty),
                func.count(OrderItem.id).filter(OrderItem.unit_cost.is_(None)),
            )
            .join(OrderItem, and_(OrderItem.order_id == Order.id, OrderItem.tenant_id == tenant_id))
            .where(*_in_range(tenant_id, start, end))  # type: ignore[arg-type]
            .group_by(Order.id, Order.total)
        )
    ).all()
    total = Decimal("0.00")
    counted = skipped = 0
    for _order_id, order_total, cost, unknown in rows:
        if unknown:
            skipped += 1
            continue
        counted += 1
        total += Decimal(order_total) - Decimal(cost or 0)
    return ProfitSummary(profit=_money(total), orders_counted=counted, orders_without_cost=skipped)


async def low_stock_count(db: AsyncSession, tenant_id: uuid.UUID) -> int:
    return int(
        (
            await db.execute(
                select(func.count())
                .select_from(InventoryItem)
                .join(Product, Product.id == InventoryItem.product_id)
                .where(
                    InventoryItem.tenant_id == tenant_id,
                    Product.deleted_at.is_(None),
                    Product.active.is_(True),
                    InventoryItem.reorder_level > 0,
                    InventoryItem.qty_on_hand <= InventoryItem.reorder_level,
                )
            )
        ).scalar_one()
    )


async def approvals_waiting(db: AsyncSession, tenant_id: uuid.UUID) -> int:
    return int(
        (
            await db.execute(
                select(func.count())
                .select_from(AgentAction)
                .where(AgentAction.tenant_id == tenant_id, AgentAction.status == ActionStatus.pending.value)
            )
        ).scalar_one()
    )


async def unpaid_udhaar(db: AsyncSession, tenant_id: uuid.UUID) -> Decimal:
    return await ledger_service.total_outstanding(db, tenant_id)
