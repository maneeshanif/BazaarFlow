"""Order and OrderItem ORM models: a sale and its lines (PRD F-007, F-008, §12.3)."""

from __future__ import annotations

import uuid
from decimal import Decimal

from sqlalchemy import CheckConstraint, ForeignKey, Index, Integer, Numeric, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.common import BaseModelMixin, TenantMixin

ORDER_STATUSES = ("draft", "posted", "reversed", "cancelled")
ORDER_CHANNELS = ("pos", "chat", "whatsapp", "voice")


class Order(BaseModelMixin, TenantMixin, Base):
    __tablename__ = "orders"
    __table_args__ = (
        CheckConstraint("status in ('draft', 'posted', 'reversed', 'cancelled')", name="ck_orders_status"),
        CheckConstraint("channel in ('pos', 'chat', 'whatsapp', 'voice')", name="ck_orders_channel"),
        CheckConstraint("discount >= 0 and discount <= subtotal", name="ck_orders_discount_range"),
        # A retried request with the same key returns the order it already created (per tenant).
        Index("uq_orders_tenant_idempotency_key", "tenant_id", "idempotency_key", unique=True),
        Index("ix_orders_tenant_created_at", "tenant_id", "created_at"),
    )
    customer_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("customers.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(12), nullable=False, default="draft")
    subtotal: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=Decimal("0.00"))
    discount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=Decimal("0.00"))
    total: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=Decimal("0.00"))
    channel: Mapped[str] = mapped_column(String(10), nullable=False, default="pos")
    idempotency_key: Mapped[str | None] = mapped_column(String(80), nullable=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    __mapper_args__ = {"version_id_col": version}


class OrderItem(BaseModelMixin, TenantMixin, Base):
    __tablename__ = "order_items"
    __table_args__ = (CheckConstraint("qty > 0", name="ck_order_items_qty_positive"),)
    order_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, index=True
    )
    product_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("products.id"), nullable=False)
    # Snapshots: a later price, cost or name change must not rewrite history or profit.
    product_name: Mapped[str] = mapped_column(String(120), nullable=False)
    qty: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    unit_cost: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
