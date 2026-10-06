"""Conversation (one customer thread on one channel) and WebhookEvent (a provider event we have already handled).

Conversation (PRD F-005, W-003): a customer is identified by their phone number on a channel. ``mode`` says who answers:
the AI or a person; switching to ``human`` stops the AI at once. ``status`` follows
``open -> ai_handling -> needs_human -> resolved`` and a new customer message reopens a resolved thread.

WebhookEvent: every inbound provider event is recorded by its provider id before it is processed, and the unique key makes
a replay a no-op (PRD I-001, build-plan task 61).
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.common import BaseModelMixin, TenantMixin, UUIDMixin, _utcnow

CONVERSATION_STATUSES = ("open", "ai_handling", "needs_human", "resolved")
CONVERSATION_MODES = ("ai", "human")


class Conversation(BaseModelMixin, TenantMixin, Base):
    __tablename__ = "conversations"
    __table_args__ = (
        CheckConstraint("status in ('open', 'ai_handling', 'needs_human', 'resolved')", name="ck_conversations_status"),
        CheckConstraint("mode in ('ai', 'human')", name="ck_conversations_mode"),
        Index("uq_conversations_tenant_channel_phone", "tenant_id", "channel", "phone", unique=True),
        Index("ix_conversations_tenant_last_message", "tenant_id", "last_message_at"),
    )
    customer_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("customers.id"), nullable=True)
    channel: Mapped[str] = mapped_column(String(20), nullable=False, default="whatsapp")
    phone: Mapped[str] = mapped_column(String(30), nullable=False)
    contact_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="open")
    mode: Mapped[str] = mapped_column(String(10), nullable=False, default="ai")
    assigned_to: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    handoff_note: Mapped[str | None] = mapped_column(String(500), nullable=True)
    last_message_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_utcnow)
    last_message_text: Mapped[str | None] = mapped_column(String(160), nullable=True)


class WebhookEvent(UUIDMixin, TenantMixin, Base):
    __tablename__ = "webhook_events"
    __table_args__ = (UniqueConstraint("tenant_id", "provider", "event_id", name="uq_webhook_events_tenant_provider_event"),)
    provider: Mapped[str] = mapped_column(String(30), nullable=False)
    event_id: Mapped[str] = mapped_column(String(120), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_utcnow)
