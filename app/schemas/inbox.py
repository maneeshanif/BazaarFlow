"""Unified inbox schemas (PRD F-005, W-003): conversations, their messages, and the context panel beside a thread."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, StringConstraints

ConversationStatus = Literal["open", "ai_handling", "needs_human", "resolved"]
Mode = Literal["ai", "human"]
MessageStatus = Literal["received", "queued", "sent", "delivered", "send_failed"]
Sender = Literal["customer", "ai", "staff"]


class ConversationOut(BaseModel):
    id: UUID
    channel: str
    phone: str
    contact_name: str | None
    customer_id: UUID | None
    status: ConversationStatus
    mode: Mode
    assigned_to: UUID | None
    handoff_note: str | None
    last_message_at: datetime
    last_message_text: str | None
    model_config = ConfigDict(from_attributes=True)


class MessageOut(BaseModel):
    id: UUID
    direction: Literal["inbound", "outbound"]
    sender: Sender | None
    text: str | None
    status: str
    error: str | None = None  # why a message could not be sent
    created_at: datetime


class RecentOrder(BaseModel):
    id: UUID
    total: Decimal
    status: str
    created_at: datetime


class ContextPanel(BaseModel):
    customer_name: str | None
    customer_phone: str | None
    balance: Decimal | None  # what they owe the shop; owners and managers only
    recent_orders: list[RecentOrder]
    suggested_actions: list[str]


class ConversationDetail(BaseModel):
    conversation: ConversationOut
    messages: list[MessageOut]  # oldest first, the latest 200
    context: ContextPanel
    provider_notice: str | None  # a banner when WhatsApp is not connected or needs reconnecting


class ReplyRequest(BaseModel):
    text: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=1000)]
    # the browser sends one per click, so a double click or a retried request cannot send twice
    idempotency_key: Annotated[str, StringConstraints(min_length=8, max_length=80, pattern=r"^[A-Za-z0-9_-]+$")] | None = None


class ConversationUpdate(BaseModel):
    """Partial update: hand the thread to a person or back to the AI, resolve or reopen it, assign it."""

    model_config = ConfigDict(extra="forbid")

    mode: Mode | None = None
    status: Literal["open", "resolved"] | None = None
    assigned_to: UUID | None = None
    unassign: bool = False
