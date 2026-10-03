"""Customer, udhaar ledger and payment schemas (PRD F-009).

Limits match the column sizes, so over-long input is a 422 and never a database error. ``balance`` is what the customer
owes the shop (positive) and is hidden from staff, who may look customers up while selling but do not see credit.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, StringConstraints, field_validator

Phone = Annotated[str, Field(pattern=r"^\+?[0-9]{7,20}$")]
Name = Annotated[str, StringConstraints(strip_whitespace=True, max_length=255)]
Money = Annotated[Decimal, Field(gt=0, max_digits=14, decimal_places=2)]


class CustomerCreate(BaseModel):
    phone: Phone
    name: Name | None = None
    email: EmailStr | None = None
    address: Annotated[str, StringConstraints(strip_whitespace=True, max_length=512)] | None = None

    @field_validator("name", "email", "address", mode="before")
    @classmethod
    def _blank_is_none(cls, value: object) -> object:
        return None if isinstance(value, str) and not value.strip() else value


class CustomerUpdate(BaseModel):
    """Partial update; unknown fields (tenant_id, balance) are rejected."""

    model_config = ConfigDict(extra="forbid")

    phone: Phone | None = None
    name: Name | None = None
    email: EmailStr | None = None
    address: Annotated[str, StringConstraints(strip_whitespace=True, max_length=512)] | None = None

    @field_validator("name", "email", "address", mode="before")
    @classmethod
    def _blank_is_none(cls, value: object) -> object:
        return None if isinstance(value, str) and not value.strip() else value


class CustomerOut(BaseModel):
    id: UUID
    tenant_id: UUID
    phone: str
    name: str | None
    email: str | None
    address: str | None
    balance: Decimal | None = None  # owed to the shop; None for staff
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class LedgerEntryOut(BaseModel):
    id: UUID
    direction: Literal["debit", "credit"]  # debit = they owe more, credit = they paid
    amount: Decimal
    ref_type: str | None
    ref_id: UUID | None
    created_at: datetime
    balance_after: Decimal  # running balance, oldest first
    model_config = ConfigDict(from_attributes=True)


class PaymentCreate(BaseModel):
    """A customer settling part or all of what they owe."""

    amount: Money
    method: Literal["cash", "card", "bank", "wallet"]


class PaymentOut(BaseModel):
    id: UUID
    customer_id: UUID | None
    amount: Decimal
    method: str
    created_at: datetime
    balance: Decimal  # what they still owe after this payment
    model_config = ConfigDict(from_attributes=True)
