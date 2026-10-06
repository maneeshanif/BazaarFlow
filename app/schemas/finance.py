"""Finance overview, cash book and finance dashboard schemas (PRD F-013, D-002, R-004, R-005).

Every figure is worked out on the server, never in the browser. ``gross_margin`` and ``payables`` are owner-only: a
manager sees the revenue, the cash/credit split and the receivables.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel

from app.schemas.dashboard import DashboardRange, MoneyFigure


class FinanceTrendDay(BaseModel):
    day: date
    revenue: Decimal
    orders: int


class GrossMargin(BaseModel):
    margin_percent: int | None  # None when no order has a known cost
    profit: Decimal
    revenue_counted: Decimal  # revenue of the orders whose every line has a cost
    orders_without_cost: int  # left out: their profit cannot be known


class AgingBucket(BaseModel):
    label: str
    amount: Decimal
    customers: int


class Receivables(BaseModel):
    total: Decimal
    buckets: list[AgingBucket]  # by how long the oldest unpaid credit sale has waited


class Payables(BaseModel):
    total: Decimal
    overdue: Decimal
    vendors: int


class CashCreditSplit(BaseModel):
    paid_now: Decimal  # the part of sales paid at the counter
    on_credit: Decimal  # the part put on udhaar
    credit_percent: int | None  # None when there were no sales


class FinanceOverview(BaseModel):
    role: str
    range: DashboardRange
    revenue: MoneyFigure
    trend: list[FinanceTrendDay]  # oldest first
    split: CashCreditSplit
    receivables: Receivables
    gross_margin: GrossMargin | None  # owner only
    payables: Payables | None  # owner only
    is_empty: bool  # nothing sold, owed or billed yet: the page shows an empty state
    generated_at: datetime


class CashBookEntry(BaseModel):
    id: UUID
    created_at: datetime
    direction: Literal["in", "out"]  # in = money received, out = money paid to a vendor
    kind: Literal["sale_payment", "udhaar_payment", "vendor_payment"]
    amount: Decimal
    method: str
    party_id: UUID | None  # the customer or vendor, when there is one
