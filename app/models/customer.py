"""Customer ORM model � per-vendor customer record."""
from __future__ import annotations
from sqlalchemy import String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base
from app.models.common import BaseModelMixin

class Customer(BaseModelMixin, Base):
    __tablename__ = "customers"
    vendor_id: Mapped[str] = mapped_column(String(36), ForeignKey("vendors.id"), nullable=False, index=True)
    phone: Mapped[str] = mapped_column(String(30), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=True)
    email: Mapped[str] = mapped_column(String(255), nullable=True)
    address: Mapped[str] = mapped_column(String(512), nullable=True)
