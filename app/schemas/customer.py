"""Customer request/response schemas."""
from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel


class CustomerCreate(BaseModel):
    phone: str
    name: str | None = None
    email: str | None = None
    address: str | None = None

class CustomerOut(BaseModel):
    id: UUID
    tenant_id: UUID
    phone: str
    name: str | None
    email: str | None
    address: str | None
    model_config = {"from_attributes": True}
