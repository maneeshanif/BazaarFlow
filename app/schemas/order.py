"""Sale (F-007) and order (F-008) schemas.

Money is NUMERIC(14,2) end to end: ``Decimal`` in, ``Decimal`` out (serialised as an exact string), never a float.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, Field, StringConstraints, field_validator, model_validator

Money = Annotated[Decimal, Field(ge=0, max_digits=14, decimal_places=2)]
SalePaymentMethod = Literal["cash", "card", "bank", "wallet", "udhaar"]


class SaleLine(BaseModel):
    product_id: UUID
    qty: int = Field(gt=0, le=1_000_000)
    unit_price: Money | None = None  # defaults to the product's current price


class SaleCreate(BaseModel):
    """PRD F-007 New sale. The channel is set by the source (here: the point of sale), never by the caller."""

    customer_id: UUID | None = None  # empty = walk-in
    items: list[SaleLine] = Field(min_length=1, max_length=100)
    discount: Money = Decimal("0.00")
    payment_method: SalePaymentMethod
    amount_paid: Money | None = None  # defaults to the total; the rest goes on the customer's udhaar
    note: Annotated[str, StringConstraints(strip_whitespace=True, max_length=500)] | None = None
    stock_override: bool = False  # sell more than the shelf count says; managers and owners only

    @field_validator("note", mode="before")
    @classmethod
    def _blank_note(cls, value: object) -> object:
        return None if isinstance(value, str) and not value.strip() else value

    @model_validator(mode="after")
    def _payment_shape(self) -> SaleCreate:
        if self.payment_method == "udhaar" and self.amount_paid not in (None, Decimal("0")):
            raise ValueError("amount_paid must be 0 for a sale on credit; choose how they paid for the part they paid")
        return self


class ReverseRequest(BaseModel):
    """Why a posted sale is being undone (kept in the audit log and on the order)."""

    reason: Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=255)]


class SalePreviewRequest(BaseModel):
    """What the New sale form asks the server to add up (the browser never does money arithmetic)."""

    items: list[SaleLine] = Field(default_factory=list, max_length=100)
    discount: Money = Decimal("0.00")
    payment_method: SalePaymentMethod | None = None
    amount_paid: Money | None = None


class SalePreviewLine(BaseModel):
    product_id: UUID
    product_name: str
    unit_price: Decimal
    line_total: Decimal
    available: int  # on the shelf right now
    enough_stock: bool  # for the quantity asked, counting every line of the same product


class SalePreview(BaseModel):
    lines: list[SalePreviewLine]
    subtotal: Decimal
    discount: Decimal
    total: Decimal
    amount_paid: Decimal
    amount_due: Decimal  # the part that would go on the customer's udhaar
    warnings: list[str]


class OrderItemOut(BaseModel):
    id: UUID
    product_id: UUID
    product_name: str
    qty: int
    unit_price: Decimal
    unit_cost: Decimal | None  # hidden from staff
    line_total: Decimal


class OrderPaymentOut(BaseModel):
    id: UUID
    amount: Decimal
    method: str
    status: str
    created_at: datetime


class OrderSummary(BaseModel):
    id: UUID
    status: str
    channel: str
    customer_id: UUID | None
    customer_name: str | None
    subtotal: Decimal
    discount: Decimal
    total: Decimal
    amount_paid: Decimal
    amount_due: Decimal  # sold on credit: what the customer still owes for this order
    item_count: int
    created_at: datetime


class OrderDetail(OrderSummary):
    note: str | None
    created_by: UUID | None
    items: list[OrderItemOut]
    payments: list[OrderPaymentOut]
    updated_at: datetime
