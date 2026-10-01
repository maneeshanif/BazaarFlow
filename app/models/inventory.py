"""InventoryItem ORM model � product catalog per vendor."""
from __future__ import annotations

from sqlalchemy import Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.common import BaseModelMixin, TenantMixin


class InventoryItem(BaseModelMixin, TenantMixin, Base):
    __tablename__ = "inventory_items"
    __table_args__ = (UniqueConstraint("tenant_id", "sku", name="uq_inventory_items_tenant_sku"),)
    sku: Mapped[str] = mapped_column(String(100), nullable=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=True)
    stock_count: Mapped[int] = mapped_column(Integer, default=0)
    price: Mapped[str] = mapped_column(String(50), nullable=True)
    incoming_units: Mapped[int] = mapped_column(Integer, default=0)
    min_threshold: Mapped[int] = mapped_column(Integer, default=0)
    description: Mapped[str] = mapped_column(Text, nullable=True)
