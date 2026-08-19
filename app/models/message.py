"""Message ORM model � inbound/outbound WhatsApp chat transcripts."""
from __future__ import annotations
import enum
from sqlalchemy import String, ForeignKey, Text, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base
from app.models.common import BaseModelMixin

class MessageDirection(str, enum.Enum):
    inbound = "inbound"
    outbound = "outbound"

class Message(BaseModelMixin, Base):
    __tablename__ = "messages"
    vendor_id: Mapped[str] = mapped_column(String(36), ForeignKey("vendors.id"), nullable=False, index=True)
    customer_id: Mapped[str] = mapped_column(String(36), ForeignKey("customers.id"), nullable=True)
    phone: Mapped[str] = mapped_column(String(30), nullable=False)
    direction: Mapped[MessageDirection] = mapped_column(SAEnum(MessageDirection), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="delivered")
    wa_message_id: Mapped[str] = mapped_column(String(255), nullable=True)
