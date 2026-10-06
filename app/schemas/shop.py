"""Shop profile and settings schemas (PRD F-020).

The owner edits the shop's name, phone, city and the largest sale the AI may post without asking. Plan, currency,
timezone and the monthly AI allowance are shown but not editable here (they are set by BazaarFlow).
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator

ShopName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=80)]
City = Annotated[str, StringConstraints(strip_whitespace=True, max_length=60)]
Phone = Annotated[str, Field(pattern=r"^\+[1-9][0-9]{7,14}$")]  # E.164, like sign-up
Limit = Annotated[Decimal, Field(ge=0, le=Decimal("10000000"), max_digits=14, decimal_places=2)]


class ShopSettingsUpdate(BaseModel):
    """Partial update. Unknown fields (plan, currency, tenant_id, agents_enabled) are rejected."""

    model_config = ConfigDict(extra="forbid")

    name: ShopName | None = None
    owner_phone: Phone | None = None
    city: City | None = None
    # null clears the shop's own limit and goes back to the platform default
    auto_post_limit: Limit | None = None

    @field_validator("city", mode="before")
    @classmethod
    def _blank_city_is_none(cls, value: object) -> object:
        return None if isinstance(value, str) and not value.strip() else value


class ShopSettingsOut(BaseModel):
    id: UUID
    name: str
    slug: str
    plan: str
    currency: str
    timezone: str
    owner_phone: str | None
    city: str | None
    onboarding_state: str
    agents_enabled: bool
    agent_cap_usd: Decimal | None
    auto_post_limit: Decimal | None  # the shop's own limit; null = the platform default
    effective_auto_post_limit: Decimal  # what the AI actually applies today
    created_at: datetime
    updated_at: datetime
