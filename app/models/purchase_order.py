"""Draft purchase orders (PRD W-006 step 3): what the shop intends to buy from a vendor when stock runs low.

A purchase order is created by the low-stock recipe next to the reorder message it files for approval. It moves
``drafted -> approved -> sent`` (the message was approved and sent) or ``cancelled`` (the owner dropped it). It never
changes stock or money: receiving goods and paying the vendor stay manual (bills and payments, F-012).
"""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, Numeric, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.common import BaseModelMixin, TenantMixin

PO_STATUSES = ("drafted", "approved", "sent", "cancelled")


class PurchaseOrder(BaseModelMixin, TenantMixin, Base):
    __tablename__ = "purchase_orders"
    __table_args__ = (
        CheckConstraint("status in ('drafted', 'approved', 'sent', 'cancelled')", name="ck_purchase_orders_status"),
        CheckConstraint("total >= 0", name="ck_purchase_orders_total_not_negative"),
        Index("ix_purchase_orders_tenant_status", "tenant_id", "status"),
        Index("ix_purchase_orders_tenant_action", "tenant_id", "action_id"),
    )
    vendor_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("vendors.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(12), nullable=False, default="drafted", server_default="drafted")
    # estimate: the sum of the lines whose cost is known (a product without a cost counts for nothing)
    total: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=Decimal("0.00"))
    # the approval (agent_actions) that sends the reorder message for this order
    action_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    note: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class PurchaseOrderItem(BaseModelMixin, TenantMixin, Base):
    __tablename__ = "purchase_order_items"
    __table_args__ = (
        CheckConstraint("qty > 0", name="ck_purchase_order_items_qty_positive"),
        Index("ix_purchase_order_items_tenant_order", "tenant_id", "purchase_order_id"),
    )
    purchase_order_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("purchase_orders.id", ondelete="CASCADE"), nullable=False)
    product_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("products.id"), nullable=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)  # the product's name when the order was drafted
    qty: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_cost: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
