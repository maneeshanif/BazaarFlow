"""Automation recipes (PRD F-024, W-008): a shop's toggles for the pre-built recipes and the history of their runs.

An ``automations`` row stores ``trigger``, ``conditions_json`` and ``actions_json`` so the later visual builder only edits
the same JSON. ``automation_runs`` is append-only history: ``queued -> running -> succeeded | failed``.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.common import BaseModelMixin, TenantMixin, UUIDMixin, _utcnow

RUN_STATUSES = ("queued", "running", "succeeded", "failed")


class Automation(BaseModelMixin, TenantMixin, Base):
    __tablename__ = "automations"
    __table_args__ = (UniqueConstraint("tenant_id", "key", name="uq_automations_tenant_key"),)
    key: Mapped[str] = mapped_column(String(40), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=text("false"))
    trigger: Mapped[str] = mapped_column(String(60), nullable=False)
    conditions_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    actions_json: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    consecutive_failures: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default=text("0"))


class AutomationRun(UUIDMixin, TenantMixin, Base):
    __tablename__ = "automation_runs"
    __table_args__ = (
        CheckConstraint("status in ('queued', 'running', 'succeeded', 'failed')", name="ck_automation_runs_status"),
        Index("ix_automation_runs_tenant_created", "tenant_id", "created_at"),
    )
    automation_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("automations.id", ondelete="CASCADE"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(10), nullable=False)
    trigger_source: Mapped[str] = mapped_column(String(10), nullable=False, default="schedule")  # schedule | manual
    summary: Mapped[str | None] = mapped_column(String(300), nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_utcnow)
