"""Voice schemas (PRD F-023, W-007): the agent's settings, the call list, and the assistant configuration to paste into VAPI."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Annotated, Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

CallStatus = Literal["ringing", "in_progress", "completed", "escalated", "failed"]


class VoiceSettingsIn(BaseModel):
    """F-023 settings. The consent notice cannot be blank: it is spoken at the start of every call."""

    model_config = ConfigDict(extra="forbid")

    enabled: bool
    greeting: Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=200)]
    consent_notice: Annotated[str, StringConstraints(strip_whitespace=True, min_length=10, max_length=300)]
    max_call_seconds: int = Field(ge=60, le=900)
    monthly_cap_usd: Annotated[Decimal, Field(ge=0, le=500, max_digits=6, decimal_places=2)]
    handoff_phone: Annotated[str, Field(pattern=r"^\+[1-9][0-9]{7,14}$")] | None = None
    retention_days: int = Field(ge=1, le=365)


class VoiceSettingsOut(VoiceSettingsIn):
    configured: bool  # false until saved once
    vapi_connected: bool
    month_spend_usd: str
    percent_used: int
    webhook_url: str


class VoiceCallOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    status: CallStatus
    caller_hint: str | None
    started_at: datetime
    ended_at: datetime | None
    duration_seconds: int
    ended_reason: str | None
    cost_usd: str
    turn_count: int
    avg_latency_ms: int | None
    max_latency_ms: int | None
    escalated: bool
    has_ticket: bool


class VoiceCallDetail(VoiceCallOut):
    summary: str | None  # redacted; removed after the retention period
    transcript: str | None
    handoff_note: str | None
    consent_notice: str | None
    turn_latencies_ms: list[int]
    transcript_removed: bool  # the retention period has passed


class AssistantConfig(BaseModel):
    assistant: dict[str, Any]  # create this in VAPI (only fields confirmed in VAPI's API reference are included)
    notes: list[str]  # settings to switch on in the VAPI dashboard, which this file cannot set
