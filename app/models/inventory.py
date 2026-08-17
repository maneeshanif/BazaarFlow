"""InventoryItem ORM model — product catalog per vendor."""
from __future__ import annotations
from sqlalchemy import String, ForeignKey, Numeric, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base
from app.models.common import BaseModelMixin

class InventoryItem(BaseModelMixin, Base):
    __tablename__ = "inventory_items"
    vendor_id: Mapped[str] = mapped_column(String(36), ForeignKey("vendors.id"), nullable=False, index=True)
    sku: Mapped[str] = mapped_column(String(100), nullable=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=True)
    stock_count: Mapped[int] = mapped_column(Integer, default=0)
    price: Mapped[str] = mapped_column(String(50), nullable=True)
    incoming_units: Mapped[int] = mapped_column(Integer, default=0)
    min_threshold: Mapped[int] = mapped_column(Integer, default=0)
    description: Mapped[str] = mapped_column(Text, nullable=True)
