"""Home dashboard schemas (PRD F-004, D-001). Every figure is worked out here, never in the browser."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel

DashboardRange = Literal["today", "7d", "30d"]


class MoneyFigure(BaseModel):
    value: Decimal
    previous: Decimal
    change_percent: int | None  # None when there is nothing to compare with


class CountFigure(BaseModel):
    value: int
    previous: int
    change_percent: int | None


class ProfitFigure(BaseModel):
    value: Decimal
    previous: Decimal
    change_percent: int | None
    orders_without_cost: int  # left out because a line has no cost, so the profit of that order cannot be known


class TrendDay(BaseModel):
    day: date
    total: Decimal
    orders: int


class DashboardOut(BaseModel):
    role: str
    range: DashboardRange
    sales: MoneyFigure
    orders: CountFigure
    low_stock: int
    profit: ProfitFigure | None  # owners and managers only: staff never see profit
    unpaid_udhaar: Decimal | None  # owners and managers only
    approvals_waiting: int | None  # owners and managers only
    briefing: str | None  # owners and managers only
    trend: list[TrendDay]  # the last 7 days, oldest first
    generated_at: datetime
