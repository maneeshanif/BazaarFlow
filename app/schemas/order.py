"""Order request/response schemas."""
from __future__ import annotations
from pydantic import BaseModel

class OrderCreate(BaseModel):
    vendor_id: str
    customer_name: str | None = None
    customer_phone: str | None = None
    product_name: str
    quantity: int = 1
    budget: str | None = None
    delivery_address: str | None = None
    notes: str | None = None

class OrderOut(BaseModel):
    id: str
    vendor_id: str
    customer_name: str | None
    customer_phone: str | None
    product_name: str
    quantity: int
    budget: str | None
    payment_status: str
    delivery_address: str | None
    notes: str | None
    model_config = {"from_attributes": True}
