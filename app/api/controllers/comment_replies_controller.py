"""Facebook comment replies API (PRD W-004 step 4): owners and managers see the proposed replies and can skip one.

Approving goes through the approvals center (``approve_comment_reply``), like a scheduled post. Role gate -> tenant-scoped
session -> service -> audit.
"""

from __future__ import annotations

from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import MANAGER_UP, get_tenant_db, require_role
from app.core.pagination import DEFAULT_LIMIT, MAX_LIMIT, Page, decode_cursor, next_cursor
from app.core.tenancy import Principal
from app.schemas.comment_replies import CommentReplyOut
from app.services import comment_reply_service

router = APIRouter()

TenantDb = Annotated[AsyncSession, Depends(get_tenant_db, scope="function")]


@router.get("/", response_model=Page[CommentReplyOut])
async def list_comment_replies(
    principal: Annotated[Principal, Depends(require_role(*MANAGER_UP))],
    db: TenantDb,
    status: Literal["proposed", "approved", "posted", "skipped", "failed"] | None = None,
    limit: Annotated[int, Query(ge=1, le=MAX_LIMIT)] = DEFAULT_LIMIT,
    cursor: Annotated[str | None, Query(max_length=60)] = None,
) -> Page[CommentReplyOut]:
    offset = decode_cursor(cursor)
    items, total = await comment_reply_service.list_replies(db, principal, status=status, limit=limit, offset=offset)
    return Page[CommentReplyOut](items=items, total=total, next_cursor=next_cursor(offset, limit, total))


@router.post("/{reply_id}/skip", response_model=CommentReplyOut)
async def skip_comment_reply(
    reply_id: UUID, principal: Annotated[Principal, Depends(require_role(*MANAGER_UP))], db: TenantDb
) -> CommentReplyOut:
    return await comment_reply_service.skip(db, principal, reply_id)
