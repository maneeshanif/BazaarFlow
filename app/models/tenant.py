"""Tenant (one retail business) and the tenancy tables around it (PRD §12.3)."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Boolean, CheckConstraint, DateTime, ForeignKey, String, Text, UniqueConstraint, Uuid, text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.common import BaseModelMixin, TenantMixin, _utcnow


class TenantRole(str, enum.Enum):
    """Roles a user can hold inside one tenant. ``platform_admin`` is a flag on ``users``."""

    owner = "owner"
    manager = "manager"
    staff = "staff"


class Tenant(BaseModelMixin, Base):
    """The isolation boundary. RLS is keyed on this table's own ``id``."""

    __tablename__ = "tenants"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    plan: Mapped[str] = mapped_column(String(30), default="demo", nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="active", nullable=False)
    onboarding_state: Mapped[str] = mapped_column(String(40), default="created", nullable=False)
    timezone: Mapped[str] = mapped_column(String(60), default="Asia/Karachi", nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="PKR", nullable=False)
    owner_phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    city: Mapped[str | None] = mapped_column(String(60), nullable=True)
    # The owner's kill switch for the AI assistant: off means no agent run starts for this shop (no deploy needed).
    agents_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=text("true"))


class Membership(BaseModelMixin, TenantMixin, Base):
    """A user's role inside one tenant."""

    __tablename__ = "memberships"
    __table_args__ = (
        UniqueConstraint("tenant_id", "user_id", name="uq_memberships_tenant_user"),
        CheckConstraint("role in ('owner', 'manager', 'staff')", name="ck_memberships_role"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    role: Mapped[str] = mapped_column(String(20), nullable=False)


class TenantIntegration(BaseModelMixin, TenantMixin, Base):
    """Per-tenant provider connection. Credentials are stored encrypted, never returned by the API."""

    __tablename__ = "tenant_integrations"
    __table_args__ = (UniqueConstraint("provider", "external_id", name="uq_tenant_integrations_provider_external"),)

    provider: Mapped[str] = mapped_column(String(40), nullable=False)
    external_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    credentials_enc: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)


class AuditLog(Base):
    """Append-only audit trail. ``tenant_id`` is NULL only for pre-tenant events such as a failed login."""

    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=True, index=True
    )
    actor_type: Mapped[str] = mapped_column(String(20), nullable=False)  # user | agent | system
    actor_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    action: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    entity: Mapped[str | None] = mapped_column(String(80), nullable=True)
    entity_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    before_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    after_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    request_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
