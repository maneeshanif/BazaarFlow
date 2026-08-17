"""Marketing request/response schemas."""
from __future__ import annotations
from datetime import datetime
from pydantic import BaseModel

class MarketingPostCreate(BaseModel):
    vendor_id: str
    title: str | None = None
    message: str | None = None
    hashtags: str | None = None
    image_url: str | None = None

class MarketingPostOut(BaseModel):
    id: str
    vendor_id: str
    title: str | None
    message: str | None
    image_url: str | None
    status: str
    model_config = {"from_attributes": True}

class ScheduledCampaignCreate(BaseModel):
    vendor_id: str
    title: str | None = None
    message: str | None = None
    scheduled_at: datetime | None = None

class ScheduledCampaignOut(BaseModel):
    id: str
    vendor_id: str
    title: str | None
    message: str | None
    scheduled_at: datetime | None
    status: str
    triggered: bool
    model_config = {"from_attributes": True}
