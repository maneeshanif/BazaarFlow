"""Voice (PRD W-007, F-023): a shop's voice agent settings and the record of each call.

``voice_calls`` keeps only what the shop needs: who (the last four digits of the caller's number), when, how long, how it
ended, what it cost, how fast each turn was, and a redacted summary and transcript that are deleted after
``voice_settings.retention_days``. The full caller number never leaves the provider.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.common import BaseModelMixin, TenantMixin

CALL_STATUSES = ("ringing", "in_progress", "completed", "escalated", "failed")
DEFAULT_CONSENT = "This call may be recorded and transcribed to help us serve you. By staying on the line you agree."


class VoiceSettings(BaseModelMixin, TenantMixin, Base):
    """One row per shop. A shop with no row has the voice agent off."""

    __tablename__ = "voice_settings"
    __table_args__ = (
        UniqueConstraint("tenant_id", name="uq_voice_settings_tenant"),
        CheckConstraint("max_call_seconds between 60 and 900", name="ck_voice_settings_max_call_seconds"),
        CheckConstraint("retention_days between 1 and 365", name="ck_voice_settings_retention_days"),
        CheckConstraint("monthly_cap_usd >= 0", name="ck_voice_settings_cap"),
    )
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=text("false"))
    greeting: Mapped[str] = mapped_column(String(200), nullable=False, default="Hello, thanks for calling. How can I help?")
    consent_notice: Mapped[str] = mapped_column(String(300), nullable=False, default=DEFAULT_CONSENT)
    max_call_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=300)
    monthly_cap_usd: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=False, default=Decimal("5.00"))
    handoff_phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    retention_days: Mapped[int] = mapped_column(Integer, nullable=False, default=30)


class VoiceCall(BaseModelMixin, TenantMixin, Base):
    __tablename__ = "voice_calls"
    __table_args__ = (
        UniqueConstraint("tenant_id", "provider_call_id", name="uq_voice_calls_tenant_provider_call"),
        CheckConstraint("status in ('ringing', 'in_progress', 'completed', 'escalated', 'failed')", name="ck_voice_calls_status"),
        Index("ix_voice_calls_tenant_started", "tenant_id", "started_at"),
    )
    provider_call_id: Mapped[str] = mapped_column(String(80), nullable=False)
    status: Mapped[str] = mapped_column(String(12), nullable=False, default="ringing")
    caller_hint: Mapped[str | None] = mapped_column(String(12), nullable=True)  # "…1234"
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    ended_reason: Mapped[str | None] = mapped_column(String(80), nullable=True)
    spend_micros: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)  # millionths of a US dollar
    turns_json: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)  # [{"latency_ms": 820}, ...]
    escalated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=text("false"))
    handoff_note: Mapped[str | None] = mapped_column(String(500), nullable=True)
    consent_notice: Mapped[str | None] = mapped_column(String(300), nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)  # redacted; removed after the retention period
    transcript: Mapped[str | None] = mapped_column(Text, nullable=True)  # redacted; removed after the retention period
    ticket_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("support_tickets.id"), nullable=True)
