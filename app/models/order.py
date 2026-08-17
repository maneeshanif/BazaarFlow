"""Order ORM model — sales orders captured via WhatsApp agent."""
from __future__ import annotations
from sqlalchemy import String, ForeignKey, Text, Numeric, Integer
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base
from app.models.common import BaseModelMixin

class Order(BaseModelMixin, Base):
    __tablename__ = "orders"
    vendor_id: Mapped[str] = mapped_column(String(36), ForeignKey("vendors.id"), nullable=False, index=True)
    customer_id: Mapped[str] = mapped_column(String(36), ForeignKey("customers.id"), nullable=True)
    customer_name: Mapped[str] = mapped_column(String(255), nullable=True)
    customer_phone: Mapped[str] = mapped_column(String(30), nullable=True)
    product_name: Mapped[str] = mapped_column(String(255), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    budget: Mapped[str] = mapped_column(String(100), nullable=True)
    payment_status: Mapped[str] = mapped_column(String(50), default="pending")
    delivery_address: Mapped[str] = mapped_column(Text, nullable=True)
    notes: Mapped[str] = mapped_column(Text, nullable=True)
