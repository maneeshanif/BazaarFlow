"""InventoryItem ORM model: the product catalog per tenant (replaced by products + stock_movements in phase 1)."""
from __future__ import annotations

from decimal import Decimal

from sqlalchemy import Index, Integer, Numeric, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.common import BaseModelMixin, SoftDeleteMixin, TenantMixin


class InventoryItem(BaseModelMixin, TenantMixin, SoftDeleteMixin, Base):
    __tablename__ = "inventory_items"
    __table_args__ = (
        # A sku is unique per tenant among live rows, so a soft-deleted sku can be created again.
        Index(
            "uq_inventory_items_tenant_sku",
            "tenant_id",
            "sku",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
            sqlite_where=text("deleted_at IS NULL"),
        ),
    )
    sku: Mapped[str] = mapped_column(String(100), nullable=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=True)
    stock_count: Mapped[int] = mapped_column(Integer, default=0)
    price: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    incoming_units: Mapped[int] = mapped_column(Integer, default=0)
    min_threshold: Mapped[int] = mapped_column(Integer, default=0)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    __mapper_args__ = {"version_id_col": version}
