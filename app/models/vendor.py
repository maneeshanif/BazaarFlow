"""Vendor ORM model - a supplier the shop buys from (v1 'vendor' = tenant, see tenant.py)."""
from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import CheckConstraint, Date, ForeignKey, Index, Numeric, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.common import BaseModelMixin, SoftDeleteMixin, TenantMixin


class Vendor(BaseModelMixin, TenantMixin, SoftDeleteMixin, Base):
    __tablename__ = "vendors"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    balance: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0.00"), nullable=False)


class VendorBill(BaseModelMixin, TenantMixin, Base):
    """A purchase bill from a vendor: the shop owes ``amount`` (PRD F-012). The matching debit is in ``ledger_entries``."""

    __tablename__ = "vendor_bills"
    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_vendor_bills_amount_positive"),
        Index("ix_vendor_bills_tenant_vendor", "tenant_id", "vendor_id"),
    )
    vendor_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("vendors.id"), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    reference: Mapped[str | None] = mapped_column(String(60), nullable=True)
    note: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)


class VendorPayment(BaseModelMixin, TenantMixin, Base):
    """Money the shop paid a vendor. The matching credit is in ``ledger_entries``."""

    __tablename__ = "vendor_payments"
    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_vendor_payments_amount_positive"),
        CheckConstraint("method in ('cash', 'card', 'bank', 'wallet')", name="ck_vendor_payments_method"),
        Index("ix_vendor_payments_tenant_vendor", "tenant_id", "vendor_id"),
    )
    vendor_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("vendors.id"), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    method: Mapped[str] = mapped_column(String(10), nullable=False)
    created_by: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
