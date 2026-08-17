"""SupportTicket ORM model — VAPI voice support tickets."""
from __future__ import annotations
from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base
from app.models.common import BaseModelMixin

class SupportTicket(BaseModelMixin, Base):
    __tablename__ = "support_tickets"
    contact: Mapped[str] = mapped_column(String(255), nullable=True)
    issue_summary: Mapped[str] = mapped_column(String(500), nullable=True)
    details: Mapped[str] = mapped_column(Text, nullable=True)
    preferred_channel: Mapped[str] = mapped_column(String(50), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="open")
