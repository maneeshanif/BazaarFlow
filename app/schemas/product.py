"""Product, stock and stock-movement schemas (PRD F-010, §12.3).

Limits mirror the field specification and the column sizes, so over-long or negative input is a 422 and never a
database error. ``qty_on_hand`` exists only on create (the opening stock): afterwards it changes through stock movements.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator

Money = Annotated[Decimal, Field(ge=0, max_digits=14, decimal_places=2)]
Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=120)]
Sku = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=40)]
Category = Annotated[str, StringConstraints(strip_whitespace=True, max_length=60)]


class ProductCreate(BaseModel):
    sku: Sku
    name: Name
    category: Category | None = None
    price: Money
    cost: Money | None = None
    qty_on_hand: int = Field(default=0, ge=0, le=1_000_000)
    reorder_level: int | None = Field(default=None, ge=0, le=1_000_000)
    vendor_id: UUID | None = None
    active: bool = True

    @field_validator("category")
    @classmethod
    def _blank_category_is_none(cls, value: str | None) -> str | None:
        return value or None


class ProductUpdate(BaseModel):
    """Partial update. Unknown fields are rejected, so ``qty_on_hand`` and ``tenant_id`` can never be smuggled in."""

    model_config = ConfigDict(extra="forbid")

    sku: Sku | None = None
    name: Name | None = None
    category: Category | None = None
    price: Money | None = None
    cost: Money | None = None
    reorder_level: int | None = Field(default=None, ge=0, le=1_000_000)
    vendor_id: UUID | None = None
    active: bool | None = None


class ProductOut(BaseModel):
    id: UUID
    tenant_id: UUID
    sku: str
    name: str
    category: str | None
    price: Decimal
    cost: Decimal | None  # hidden from staff: it reveals margin
    vendor_id: UUID | None
    image_url: str | None
    active: bool
    qty_on_hand: int
    reorder_level: int
    low_stock: bool
    created_at: datetime
    updated_at: datetime


class StockMovementCreate(BaseModel):
    """A manual stock change. ``delta`` is signed: positive adds stock, negative removes it."""

    delta: int = Field(ge=-1_000_000, le=1_000_000)
    reason: Literal["purchase", "adjustment", "return"]
    note: str | None = Field(default=None, max_length=255)

    @field_validator("delta")
    @classmethod
    def _non_zero(cls, value: int) -> int:
        if value == 0:
            raise ValueError("must not be zero")
        return value


class StockMovementOut(BaseModel):
    id: UUID
    product_id: UUID
    delta: int
    reason: str
    ref_type: str | None
    ref_id: UUID | None
    actor_type: str
    actor_id: str | None
    note: str | None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)
