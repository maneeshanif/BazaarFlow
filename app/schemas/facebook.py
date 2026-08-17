"""Facebook account request/response schemas."""
from __future__ import annotations
from pydantic import BaseModel

class FacebookAccountCreate(BaseModel):
    vendor_id: str
    page_id: str
    page_name: str | None = None
    access_token: str

class FacebookAccountOut(BaseModel):
    id: str
    vendor_id: str
    page_id: str
    page_name: str | None
    model_config = {"from_attributes": True}
