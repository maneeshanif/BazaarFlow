"""Payment and LedgerEntry ORM models: money received and the udhaar (customer credit) ledger (PRD F-007, F-009)."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Numeric, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.common import BaseModelMixin, TenantMixin, UUIDMixin, _utcnow

PAYMENT_METHODS = ("cash", "card", "bank", "wallet", "udhaar")


class Payment(BaseModelMixin, TenantMixin, Base):
    """Money actually received. A sale on credit has no payment for the unpaid part; that is a ledger debit."""

    __tablename__ = "payments"
    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_payments_amount_positive"),
        CheckConstraint("method in ('cash', 'card', 'bank', 'wallet')", name="ck_payments_method"),
        CheckConstraint("status in ('completed', 'reversed')", name="ck_payments_status"),
        Index("ix_payments_tenant_created_at", "tenant_id", "created_at"),
    )
    order_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("orders.id"), nullable=True, index=True)
    customer_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("customers.id"), nullable=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    method: Mapped[str] = mapped_column(String(10), nullable=False)
    status: Mapped[str] = mapped_column(String(10), nullable=False, default="completed")
    created_by: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)


class LedgerEntry(UUIDMixin, TenantMixin, Base):
    """Append-only party ledger. For a customer: debit = they owe more (credit sale), credit = they paid."""

    __tablename__ = "ledger_entries"
    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_ledger_entries_amount_positive"),
        CheckConstraint("party_type in ('customer', 'vendor')", name="ck_ledger_entries_party_type"),
        CheckConstraint("direction in ('debit', 'credit')", name="ck_ledger_entries_direction"),
        Index("ix_ledger_entries_tenant_party", "tenant_id", "party_type", "party_id"),
    )
    party_type: Mapped[str] = mapped_column(String(10), nullable=False)
    party_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    direction: Mapped[str] = mapped_column(String(6), nullable=False)
    ref_type: Mapped[str | None] = mapped_column(String(30), nullable=True)
    ref_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
