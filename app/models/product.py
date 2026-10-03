"""Product ORM model: the catalog entry a tenant sells (PRD F-010, §12.3). Stock lives in inventory_items."""

from __future__ import annotations

import uuid
from decimal import Decimal

from sqlalchemy import Boolean, ForeignKey, Index, Numeric, String, Uuid, text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.common import BaseModelMixin, SoftDeleteMixin, TenantMixin


class Product(BaseModelMixin, TenantMixin, SoftDeleteMixin, Base):
    __tablename__ = "products"
    __table_args__ = (
        # A sku is unique per tenant among live rows, so a soft-deleted sku can be created again.
        Index(
            "uq_products_tenant_sku",
            "tenant_id",
            "sku",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
            sqlite_where=text("deleted_at IS NULL"),
        ),
    )
    sku: Mapped[str] = mapped_column(String(40), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    category: Mapped[str | None] = mapped_column(String(60), nullable=True)
    price: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    cost: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    vendor_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("vendors.id"), nullable=True)
    # Object path inside the private storage bucket (starts with the tenant id); never a public URL.
    image_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=text("true"))
