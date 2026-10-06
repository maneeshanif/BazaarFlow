"""System logs (PRD F-028): the platform operator's read-only view of the audit trail across shops."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class LogRow(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime
    tenant_id: UUID | None
    tenant_name: str | None
    actor_type: str
    actor_id: str | None
    action: str
    entity: str | None
    entity_id: str | None
    request_id: str | None


class LogDetail(LogRow):
    before: dict[str, Any] | None
    after: dict[str, Any] | None  # secrets were masked when the row was written
