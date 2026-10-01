"""Server-side context handed to every agent tool call (PRD §36.2-36.3).

Tenant, user and role come from the authenticated request, never from model output. The session is the
caller's tenant-scoped transaction, so row-level security applies to everything a tool reads or writes.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tenant import TenantRole


@dataclass(frozen=True)
class ToolContext:
    tenant_id: uuid.UUID
    user_id: uuid.UUID | None
    role: TenantRole
    session: AsyncSession
