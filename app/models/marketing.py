"""MarketingPost + ScheduledCampaign ORM models."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Index, Integer, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.common import BaseModelMixin, TenantMixin


class MarketingPost(BaseModelMixin, TenantMixin, Base):
    __tablename__ = "marketing_posts"
    __table_args__ = (Index("ix_marketing_posts_tenant_status_due", "tenant_id", "status", "scheduled_for"),)
    title: Mapped[str] = mapped_column(String(255), nullable=True)
    message: Mapped[str] = mapped_column(Text, nullable=True)
    hashtags: Mapped[str] = mapped_column(Text, nullable=True)
    image_url: Mapped[str] = mapped_column(Text, nullable=True)
    fb_post_id: Mapped[str] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="draft")
    # Phase 2 (W-004): when it should go out, when it did, how many tries, and why the last one failed.
    scheduled_for: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default=text("0"))
    last_error: Mapped[str | None] = mapped_column(String(500), nullable=True)
    source: Mapped[str] = mapped_column(String(10), nullable=False, default="manual", server_default=text("'manual'"))
    # W-004 step 4: when the scheduler last read this post's Facebook comments
    comments_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

class ScheduledCampaign(BaseModelMixin, TenantMixin, Base):
    __tablename__ = "scheduled_campaigns"
    title: Mapped[str] = mapped_column(String(255), nullable=True)
    message: Mapped[str] = mapped_column(Text, nullable=True)
    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="pending")
    triggered: Mapped[bool] = mapped_column(default=False)
