"""Vendor ORM model � one vendor = one WhatsApp Business account."""
from __future__ import annotations

from typing import Any

from sqlalchemy import JSON, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.common import BaseModelMixin


class Vendor(BaseModelMixin, Base):
    __tablename__ = "vendors"
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    phone_number_id: Mapped[str] = mapped_column(String(100), nullable=True)
    waba_id: Mapped[str] = mapped_column(String(100), nullable=True)
    access_token: Mapped[str] = mapped_column(String(512), nullable=True)
    settings: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
