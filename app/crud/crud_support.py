"""CRUD operations for the SupportTicket entity.

Every function takes the ``tenant_id`` explicitly and filters on it. This is defense in depth on top
of Postgres row-level security (PRD §3.5). Functions flush but never commit: the request dependency
owns the transaction so the transaction-local ``app.tenant_id`` setting stays in force.
"""
from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.support import SupportTicket


async def create_ticket(db: AsyncSession, tenant_id: UUID, **kwargs: Any) -> SupportTicket:
    ticket = SupportTicket(tenant_id=tenant_id, **kwargs)
    db.add(ticket)
    await db.flush()
    await db.refresh(ticket)
    return ticket
