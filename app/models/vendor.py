"""Vendor ORM model � one vendor = one WhatsApp Business account."""
from __future__ import annotations
from sqlalchemy import String, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
from app.models.common import BaseModelMixin

class Vendor(BaseModelMixin, Base):
    __tablename__ = "vendors"
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    phone_number_id: Mapped[str] = mapped_column(String(100), nullable=True)
    waba_id: Mapped[str] = mapped_column(String(100), nullable=True)
    access_token: Mapped[str] = mapped_column(String(512), nullable=True)
    settings: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
