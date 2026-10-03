"""StockMovement ORM model: every quantity change is a row (PRD §12.3: never change quantity without one)."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.common import TenantMixin, UUIDMixin, _utcnow

STOCK_REASONS = ("opening", "sale", "purchase", "adjustment", "return", "reversal")


class StockMovement(UUIDMixin, TenantMixin, Base):
    """Append-only: the application role may insert and read, never update or delete."""

    __tablename__ = "stock_movements"
    __table_args__ = (
        CheckConstraint("delta <> 0", name="ck_stock_movements_delta_not_zero"),
        CheckConstraint(
            "reason in ('opening', 'sale', 'purchase', 'adjustment', 'return', 'reversal')",
            name="ck_stock_movements_reason",
        ),
        CheckConstraint("actor_type in ('user', 'agent', 'system')", name="ck_stock_movements_actor_type"),
    )
    product_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("products.id"), nullable=False, index=True)
    delta: Mapped[int] = mapped_column(Integer, nullable=False)
    reason: Mapped[str] = mapped_column(String(20), nullable=False)
    ref_type: Mapped[str | None] = mapped_column(String(30), nullable=True)
    ref_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    actor_type: Mapped[str] = mapped_column(String(10), nullable=False, default="user")
    actor_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    note: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False, index=True)
