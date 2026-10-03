"""What a running agent carries: who is asking, the shop's database session, and a record of what it did."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.agent_runtime.redact import Redactor
from app.agents.context import ToolContext
from app.core.tenancy import Principal


@dataclass
class ProposedAction:
    """An approval the agent filed during this run."""

    id: uuid.UUID
    tool: str
    summary: str


@dataclass
class TraceStep:
    tool: str
    arguments: dict[str, Any]
    result: str
    ok: bool


@dataclass
class RuntimeContext:
    """Tenant, user and role come from the authenticated request, never from anything the model says."""

    principal: Principal
    db: AsyncSession
    session_id: str
    redactor: Redactor = field(default_factory=Redactor)
    actions: list[ProposedAction] = field(default_factory=list)
    steps: list[TraceStep] = field(default_factory=list)

    def tool_context(self) -> ToolContext:
        return ToolContext(
            tenant_id=self.principal.tenant_id,
            user_id=self.principal.user_id,
            role=self.principal.role,
            session=self.db,
        )
