"""Shared SQLAlchemy mixins and base utilities."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Uuid
from sqlalchemy.orm import Mapped, mapped_column


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class UUIDMixin:
    """Native UUID v4 primary key mixin."""

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)


class TimestampMixin:
    """Automatic created_at / updated_at timestamps."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_utcnow,
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_utcnow,
        onupdate=_utcnow,
        nullable=False,
    )


class BaseModelMixin(UUIDMixin, TimestampMixin):
    """Combines UUID PK + timestamps. Use as base for all models."""


class TenantMixin:
    """Adds the tenant isolation column (PRD §3.5).

    Every business table uses this mixin. The migration enables and forces row-level security on
    the table, and an architecture test fails if a table has neither.
    """

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
