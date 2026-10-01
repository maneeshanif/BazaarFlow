"""One place to write audit rows (PRD §14.1) and to mask sensitive values before they are stored."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tenant import AuditLog

_SENSITIVE_PARTS = ("password", "token", "secret", "authorization", "credential", "api_key", "apikey")
MASK = "***"


def mask_email(email: str) -> str:
    local, _, domain = email.partition("@")
    return f"{local[:1]}***@{domain}" if domain else MASK


def mask_sensitive(value: Any) -> Any:
    """Recursively replace the value of any key that looks like a secret with ``***``."""
    if isinstance(value, dict):
        return {
            k: MASK if any(part in str(k).lower() for part in _SENSITIVE_PARTS) else mask_sensitive(v)
            for k, v in value.items()
        }
    if isinstance(value, list):
        return [mask_sensitive(v) for v in value]
    return value


def record_audit(
    session: AsyncSession,
    action: str,
    *,
    tenant_id: uuid.UUID | None,
    actor_type: str = "user",
    actor_id: uuid.UUID | str | None = None,
    entity: str | None = None,
    entity_id: uuid.UUID | str | None = None,
    before: dict[str, Any] | None = None,
    after: dict[str, Any] | None = None,
    request_id: str | None = None,
) -> AuditLog:
    """Add one audit row to the caller's transaction (it commits or rolls back with the change itself)."""
    row = AuditLog(
        tenant_id=tenant_id,
        actor_type=actor_type,
        actor_id=str(actor_id) if actor_id is not None else None,
        action=action,
        entity=entity,
        entity_id=str(entity_id) if entity_id is not None else None,
        before_json=mask_sensitive(before) if before is not None else None,
        after_json=mask_sensitive(after) if after is not None else None,
        request_id=request_id,
    )
    session.add(row)
    return row
