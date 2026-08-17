"""User ORM model — supports multi-role auth."""
from __future__ import annotations
import enum
from sqlalchemy import String, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base
from app.models.common import BaseModelMixin

class UserRole(str, enum.Enum):
    admin = "admin"
    vendor = "vendor"
    staff = "staff"
    customer = "customer"

class User(BaseModelMixin, Base):
    __tablename__ = "users"
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=True)
    role: Mapped[UserRole] = mapped_column(SAEnum(UserRole), default=UserRole.vendor, nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True)
