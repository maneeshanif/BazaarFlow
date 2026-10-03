"""InventoryItem ORM model: the stock level of one product (PRD §12.3). Quantity changes only via stock_movements."""

from __future__ import annotations

import uuid

from sqlalchemy import CheckConstraint, ForeignKey, Integer, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.common import BaseModelMixin, TenantMixin


class InventoryItem(BaseModelMixin, TenantMixin, Base):
    __tablename__ = "inventory_items"
    __table_args__ = (
        CheckConstraint("qty_on_hand >= 0", name="ck_inventory_items_qty_non_negative"),
        UniqueConstraint("tenant_id", "product_id", name="uq_inventory_items_tenant_product"),
    )
    product_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    qty_on_hand: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    reorder_level: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    __mapper_args__ = {"version_id_col": version}
