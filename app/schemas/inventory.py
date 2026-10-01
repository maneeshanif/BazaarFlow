"""Inventory request/response schemas."""
from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel


class InventoryItemCreate(BaseModel):
    sku: str | None = None
    name: str
    category: str | None = None
    stock_count: int = 0
    price: str | None = None
    incoming_units: int = 0
    min_threshold: int = 0
    description: str | None = None

class InventoryItemOut(BaseModel):
    id: UUID
    tenant_id: UUID
    sku: str | None
    name: str
    category: str | None
    stock_count: int
    price: str | None
    incoming_units: int
    min_threshold: int
    model_config = {"from_attributes": True}
