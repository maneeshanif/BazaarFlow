"""Customer request/response schemas."""
from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field


class CustomerCreate(BaseModel):
    """Limits match the column sizes, so over-long input is a 422 and never a database error."""

    phone: str = Field(pattern=r"^\+?[0-9]{7,20}$")
    name: str | None = Field(default=None, max_length=255)
    email: str | None = Field(default=None, max_length=255)
    address: str | None = Field(default=None, max_length=512)

class CustomerOut(BaseModel):
    id: UUID
    tenant_id: UUID
    phone: str
    name: str | None
    email: str | None
    address: str | None
    model_config = {"from_attributes": True}
