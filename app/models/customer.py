"""Customer ORM model: a tenant's customer record."""
from __future__ import annotations

from sqlalchemy import Index, String, text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.common import BaseModelMixin, SoftDeleteMixin, TenantMixin


class Customer(BaseModelMixin, TenantMixin, SoftDeleteMixin, Base):
    __tablename__ = "customers"
    __table_args__ = (
        # A phone number is unique per tenant among live customers.
        Index(
            "uq_customers_tenant_phone",
            "tenant_id",
            "phone",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
            sqlite_where=text("deleted_at IS NULL"),
        ),
    )
    phone: Mapped[str] = mapped_column(String(30), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=True)
    email: Mapped[str] = mapped_column(String(255), nullable=True)
    address: Mapped[str] = mapped_column(String(512), nullable=True)
