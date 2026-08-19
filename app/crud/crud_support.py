"""CRUD operations for the SupportTicket entity."""
from __future__ import annotations
from typing import List
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.support import SupportTicket


async def get_tickets_by_vendor(
    db: AsyncSession, vendor_id: UUID
) -> List[SupportTicket]:
    result = await db.execute(
        select(SupportTicket).where(SupportTicket.vendor_id == vendor_id)
    )
    return list(result.scalars().all())


async def create_ticket(db: AsyncSession, **kwargs) -> SupportTicket:
    ticket = SupportTicket(**kwargs)
    db.add(ticket)
    await db.commit()
    await db.refresh(ticket)
    return ticket
