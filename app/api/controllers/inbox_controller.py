"""Unified inbox API (PRD F-005): every role in the shop can read and answer conversations."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import ALL_ROLES, get_tenant_db, require_role
from app.core.pagination import DEFAULT_LIMIT, MAX_LIMIT, Page, decode_cursor, next_cursor
from app.core.tenancy import Principal
from app.schemas.inbox import (
    ConversationDetail,
    ConversationOut,
    ConversationStatus,
    ConversationUpdate,
    MessageOut,
    ReplyRequest,
)
from app.services import inbox_service

router = APIRouter()

TenantDb = Annotated[AsyncSession, Depends(get_tenant_db, scope="function")]
Member = Annotated[Principal, Depends(require_role(*ALL_ROLES))]


@router.get("/", response_model=Page[ConversationOut])
async def list_conversations(
    principal: Member,
    db: TenantDb,
    status_filter: Annotated[ConversationStatus | None, Query(alias="status")] = None,
    q: Annotated[str | None, Query(max_length=80)] = None,
    limit: Annotated[int, Query(ge=1, le=MAX_LIMIT)] = DEFAULT_LIMIT,
    cursor: Annotated[str | None, Query(max_length=60)] = None,
) -> Page[ConversationOut]:
    offset = decode_cursor(cursor)
    items, total = await inbox_service.list_conversations(db, principal, status=status_filter, q=q, limit=limit, offset=offset)
    return Page[ConversationOut](items=items, total=total, next_cursor=next_cursor(offset, limit, total))


@router.get("/{conversation_id}", response_model=ConversationDetail)
async def get_conversation(conversation_id: UUID, principal: Member, db: TenantDb) -> ConversationDetail:
    return await inbox_service.get_conversation(db, principal, conversation_id)


@router.patch("/{conversation_id}", response_model=ConversationOut)
async def update_conversation(conversation_id: UUID, body: ConversationUpdate, principal: Member, db: TenantDb) -> ConversationOut:
    """Switch AI / Human, resolve or reopen, assign. Switching to Human stops the AI for this conversation at once."""
    return await inbox_service.update_conversation(db, principal, conversation_id, body)


@router.post("/{conversation_id}/messages", response_model=MessageOut, status_code=status.HTTP_201_CREATED)
async def send_message(conversation_id: UUID, body: ReplyRequest, principal: Member, db: TenantDb) -> MessageOut:
    return await inbox_service.send_reply(db, principal, conversation_id, body.text, body.idempotency_key)


@router.post("/{conversation_id}/messages/{message_id}/retry", response_model=MessageOut)
async def retry_message(conversation_id: UUID, message_id: UUID, principal: Member, db: TenantDb) -> MessageOut:
    return await inbox_service.retry_message(db, principal, conversation_id, message_id)
