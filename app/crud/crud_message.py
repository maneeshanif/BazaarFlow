"""CRUD operations for the Message entity."""
from __future__ import annotations
from typing import List
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.message import Message


async def get_messages_by_customer(
    db: AsyncSession, customer_id: UUID
) -> List[Message]:
    result = await db.execute(
        select(Message).where(Message.customer_id == customer_id).order_by(Message.created_at)
    )
    return list(result.scalars().all())


async def create_message(db: AsyncSession, **kwargs) -> Message:
    msg = Message(**kwargs)
    db.add(msg)
    await db.commit()
    await db.refresh(msg)
    return msg
