"""Message ORM model � inbound/outbound WhatsApp chat transcripts."""
from __future__ import annotations

import enum
import uuid

from sqlalchemy import CheckConstraint, ForeignKey, Index, String, Text, Uuid, text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.common import BaseModelMixin, TenantMixin


class MessageDirection(str, enum.Enum):
    inbound = "inbound"
    outbound = "outbound"

class Message(BaseModelMixin, TenantMixin, Base):
    __tablename__ = "messages"
    __table_args__ = (
        CheckConstraint("sender is null or sender in ('customer', 'ai', 'staff')", name="ck_messages_sender"),
        Index(
            "uq_messages_tenant_idempotency_key",
            "tenant_id",
            "idempotency_key",
            unique=True,
            postgresql_where=text("idempotency_key IS NOT NULL"),
            sqlite_where=text("idempotency_key IS NOT NULL"),
        ),
    )
    conversation_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("conversations.id"), nullable=True, index=True
    )
    sender: Mapped[str | None] = mapped_column(String(10), nullable=True)  # customer | ai | staff
    sent_by: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    idempotency_key: Mapped[str | None] = mapped_column(String(80), nullable=True)
    error: Mapped[str | None] = mapped_column(String(200), nullable=True)  # why a send failed
    customer_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("customers.id"), nullable=True)
    phone: Mapped[str] = mapped_column(String(30), nullable=False)
    direction: Mapped[MessageDirection] = mapped_column(SAEnum(MessageDirection), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="delivered")
    wa_message_id: Mapped[str] = mapped_column(String(255), nullable=True)
