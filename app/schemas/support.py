"""Support ticket request/response schemas."""
from __future__ import annotations
from pydantic import BaseModel

class SupportTicketCreate(BaseModel):
    contact: str | None = None
    issue_summary: str | None = None
    details: str | None = None
    preferred_channel: str | None = None

class SupportTicketOut(BaseModel):
    id: str
    contact: str | None
    issue_summary: str | None
    status: str
    model_config = {"from_attributes": True}
