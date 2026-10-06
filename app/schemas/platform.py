"""Platform admin schemas (PRD F-025 tenants, D-004 platform overview). Operators only.

The tenant list never carries a shop's business data or contact details: name, plan, status, size and last activity.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, StringConstraints

from app.schemas.dashboard import CountFigure

TenantStatus = Literal["active", "suspended"]


class PlatformTenantOut(BaseModel):
    id: UUID
    name: str
    slug: str
    plan: str
    status: TenantStatus
    city: str | None
    is_demo: bool  # a visitor's temporary demo shop
    onboarding_state: str
    agents_enabled: bool
    users: int
    last_activity_at: datetime | None  # the latest order, agent run or message
    created_at: datetime


class SuspendRequest(BaseModel):
    reason: Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=200)]


class PlatformOverview(BaseModel):
    """D-004. ``error_rate_percent`` is the share of agent runs that failed in the last 7 days."""

    tenants: CountFigure  # real shops (demo shops are counted apart); previous = shops created before the last 7 days
    demo_tenants: int
    active_tenants_7d: int  # shops with an order, agent run or message in the last 7 days
    messages_today: int
    messages_per_day_7d: int  # average per day over the last 7 days
    ai_spend_month_usd: Decimal
    agent_runs_7d: int
    error_rate_percent: int | None  # None when there were no agent runs
    is_empty: bool
    generated_at: datetime
