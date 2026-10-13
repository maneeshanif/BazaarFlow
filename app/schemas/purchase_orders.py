"""Draft purchase order schemas (PRD W-006). Read-only apart from cancelling a draft: orders are drafted by the
low-stock recipe, never typed in, so there is no create or edit body."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict

POStatus = Literal["drafted", "approved", "sent", "cancelled"]


class PurchaseOrderItemOut(BaseModel):
    product_id: UUID | None
    name: str
    qty: int
    unit_cost: Decimal | None
    model_config = ConfigDict(from_attributes=True)


class PurchaseOrderOut(BaseModel):
    id: UUID
    vendor_id: UUID
    vendor_name: str
    vendor_has_phone: bool  # false: the message cannot be sent, the order stays a draft (W-006 failure path)
    status: POStatus
    total: Decimal
    item_count: int
    action_id: UUID | None
    created_at: datetime
    sent_at: datetime | None


class PurchaseOrderDetail(PurchaseOrderOut):
    items: list[PurchaseOrderItemOut]
    note: str | None
