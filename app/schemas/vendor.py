"""Vendor (supplier) request/response schemas."""
from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field


class VendorCreate(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    phone: str | None = Field(default=None, max_length=30)


class VendorUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=255)
    phone: str | None = Field(default=None, max_length=30)


class VendorOut(BaseModel):
    id: UUID
    tenant_id: UUID
    name: str
    phone: str | None
    balance: Decimal
    model_config = {"from_attributes": True}
