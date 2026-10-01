"""Facebook account request/response schemas."""
from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel


class FacebookAccountCreate(BaseModel):
    page_id: str
    page_name: str | None = None
    access_token: str

class FacebookAccountOut(BaseModel):
    id: UUID
    tenant_id: UUID
    page_id: str
    page_name: str | None
    model_config = {"from_attributes": True}
