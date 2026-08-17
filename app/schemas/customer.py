"""Customer request/response schemas."""
from __future__ import annotations
from pydantic import BaseModel

class CustomerCreate(BaseModel):
    vendor_id: str
    phone: str
    name: str | None = None
    email: str | None = None
    address: str | None = None

class CustomerOut(BaseModel):
    id: str
    vendor_id: str
    phone: str
    name: str | None
    email: str | None
    address: str | None
    model_config = {"from_attributes": True}
