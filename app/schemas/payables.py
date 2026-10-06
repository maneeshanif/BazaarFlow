"""Vendors and payables schemas (PRD F-012, R-005).

Money is ``NUMERIC(14,2)`` and strictly positive for bills and payments. ``balance`` is what the shop owes the vendor
(the sum of its ledger entries), never a stored column. Limits match the column sizes.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator

Phone = Annotated[str, Field(pattern=r"^\+?[0-9]{7,20}$")]
Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=120)]
Money = Annotated[Decimal, Field(gt=0, max_digits=14, decimal_places=2)]
Method = Literal["cash", "card", "bank", "wallet"]


def _blank_is_none(value: object) -> object:
    return None if isinstance(value, str) and not value.strip() else value


class ShopVendorCreate(BaseModel):
    name: Name
    phone: Phone | None = None

    _blank = field_validator("phone", mode="before")(_blank_is_none)


class ShopVendorUpdate(BaseModel):
    """Partial update; unknown fields (tenant_id, balance) are rejected."""

    model_config = ConfigDict(extra="forbid")

    name: Name | None = None
    phone: Phone | None = None

    _blank = field_validator("phone", mode="before")(_blank_is_none)


class ShopVendorOut(BaseModel):
    id: UUID
    tenant_id: UUID
    name: str
    phone: str | None
    balance: Decimal  # what the shop owes this vendor
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class VendorBillCreate(BaseModel):
    amount: Money
    due_date: date | None = None
    reference: Annotated[str, StringConstraints(strip_whitespace=True, max_length=60)] | None = None
    note: Annotated[str, StringConstraints(strip_whitespace=True, max_length=255)] | None = None

    _blank = field_validator("reference", "note", mode="before")(_blank_is_none)


class VendorBillOut(BaseModel):
    id: UUID
    vendor_id: UUID
    amount: Decimal
    due_date: date | None
    reference: str | None
    note: str | None
    created_at: datetime
    balance: Decimal  # the vendor's balance after this bill
    model_config = ConfigDict(from_attributes=True)


class VendorPaymentCreate(BaseModel):
    amount: Money
    method: Method


class VendorPaymentOut(BaseModel):
    id: UUID
    vendor_id: UUID
    amount: Decimal
    method: str
    created_at: datetime
    balance: Decimal  # the vendor's balance after this payment
    model_config = ConfigDict(from_attributes=True)


class VendorLedgerEntryOut(BaseModel):
    id: UUID
    direction: Literal["debit", "credit"]  # debit = a bill (owe more), credit = a payment
    amount: Decimal
    ref_type: str | None
    ref_id: UUID | None
    created_at: datetime
    balance_after: Decimal
    model_config = ConfigDict(from_attributes=True)


class PayableRow(BaseModel):
    """One vendor in the payables report (R-005)."""

    vendor_id: UUID
    name: str
    phone: str | None
    owed: Decimal
    overdue: Decimal  # the part of ``owed`` on bills already past their due date
    next_due: date | None  # the earliest due date among the bills still unpaid
