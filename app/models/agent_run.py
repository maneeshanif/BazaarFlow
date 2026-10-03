"""AgentRun: one row per chat turn an agent handled (PRD §12.3, F-022). The trace is stored already redacted."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, BigInteger, CheckConstraint, DateTime, Index, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.common import TenantMixin, UUIDMixin, _utcnow

RUN_OUTCOMES = ("ok", "failed", "step_limit", "paused", "spend_limit")


class AgentRun(UUIDMixin, TenantMixin, Base):
    """Append-only. ``input_text``, ``output_text`` and ``trace_json`` hold no personal data (see ``redact``)."""

    __tablename__ = "agent_runs"
    __table_args__ = (
        CheckConstraint("outcome in ('ok', 'failed', 'step_limit', 'paused', 'spend_limit')", name="ck_agent_runs_outcome"),
        Index("ix_agent_runs_tenant_created_at", "tenant_id", "created_at"),
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    agent: Mapped[str] = mapped_column(String(40), nullable=False)
    session_id: Mapped[str] = mapped_column(String(80), nullable=False)
    input_text: Mapped[str] = mapped_column(Text, nullable=False)
    output_text: Mapped[str] = mapped_column(Text, nullable=False)
    trace_json: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False)
    action_ids: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    outcome: Mapped[str] = mapped_column(String(12), nullable=False)
    tokens_in: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    tokens_out: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # Integer millionths of a US dollar: exact, so the monthly cap adds up without rounding drift.
    spend_micros: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    duration_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False, index=True)
