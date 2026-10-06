"""The shop's posting schedule (PRD F-015, W-004): how often the marketing agent drafts and when posts may go out."""

from __future__ import annotations

from datetime import date, time

from sqlalchemy import Boolean, CheckConstraint, Date, Integer, String, Time, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.common import BaseModelMixin, TenantMixin


class MarketingSchedule(BaseModelMixin, TenantMixin, Base):
    """One per shop. ``approval_mode`` is ``manual`` (every drafted post waits for approval) or ``auto``."""

    __tablename__ = "marketing_schedules"
    __table_args__ = (
        UniqueConstraint("tenant_id", name="uq_marketing_schedules_tenant"),
        CheckConstraint("posts_per_day between 1 and 5", name="ck_marketing_schedules_posts_per_day"),
        CheckConstraint("approval_mode in ('manual', 'auto')", name="ck_marketing_schedules_approval_mode"),
        CheckConstraint("window_start < window_end", name="ck_marketing_schedules_window"),
    )
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=text("false"))
    goal: Mapped[str] = mapped_column(String(30), nullable=False, default="general")
    notes: Mapped[str | None] = mapped_column(String(300), nullable=True)
    tone: Mapped[str] = mapped_column(String(20), nullable=False, default="friendly")
    language: Mapped[str] = mapped_column(String(12), nullable=False, default="english")
    posts_per_day: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    window_start: Mapped[time] = mapped_column(Time, nullable=False, default=time(10, 0))
    window_end: Mapped[time] = mapped_column(Time, nullable=False, default=time(20, 0))
    approval_mode: Mapped[str] = mapped_column(String(10), nullable=False, default="manual")
    last_generated_on: Mapped[date | None] = mapped_column(Date, nullable=True)
