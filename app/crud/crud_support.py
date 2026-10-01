"""CRUD operations for the SupportTicket entity."""
from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.support import SupportTicket


async def create_ticket(db: AsyncSession, **kwargs: Any) -> SupportTicket:
    ticket = SupportTicket(**kwargs)
    db.add(ticket)
    await db.commit()
    await db.refresh(ticket)
    return ticket
