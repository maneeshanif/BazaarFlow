"""Vendor request/response schemas."""
from __future__ import annotations
from pydantic import BaseModel

class VendorCreate(BaseModel):
    name: str
    phone_number_id: str | None = None
    waba_id: str | None = None
    access_token: str | None = None

class VendorUpdate(BaseModel):
    name: str | None = None
    phone_number_id: str | None = None
    waba_id: str | None = None
    access_token: str | None = None
    settings: dict | None = None

class VendorOut(BaseModel):
    id: str
    user_id: str
    name: str
    phone_number_id: str | None
    waba_id: str | None
    settings: dict
    model_config = {"from_attributes": True}
