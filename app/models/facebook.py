"""FacebookAccount ORM model � connected FB pages per vendor."""
from __future__ import annotations

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.common import BaseModelMixin, TenantMixin


class FacebookAccount(BaseModelMixin, TenantMixin, Base):
    __tablename__ = "facebook_accounts"
    page_id: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    page_name: Mapped[str] = mapped_column(String(255), nullable=True)
    access_token: Mapped[str] = mapped_column(String(512), nullable=False)
