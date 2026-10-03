"""Marketing studio API (PRD F-014): owner and manager only, tenant-scoped. Drafts only; nothing is published."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import MANAGER_UP, get_tenant_db, require_role
from app.core.pagination import DEFAULT_LIMIT, MAX_LIMIT, Page, decode_cursor
from app.core.tenancy import Principal
from app.schemas.marketing_studio import DraftRequest, PostOut, PostStatus, PostUpdate
from app.services import marketing_studio_service as studio

router = APIRouter()

TenantDb = Annotated[AsyncSession, Depends(get_tenant_db, scope="function")]
Manager = Annotated[Principal, Depends(require_role(*MANAGER_UP))]


@router.post("/drafts", response_model=PostOut, status_code=status.HTTP_201_CREATED)
async def create_draft(body: DraftRequest, principal: Manager, db: TenantDb) -> PostOut:
    return await studio.create_draft(db, principal, body)


@router.get("/", response_model=Page[PostOut])
async def list_posts(
    principal: Manager,
    db: TenantDb,
    post_status: Annotated[PostStatus | None, Query(alias="status")] = None,
    limit: Annotated[int, Query(ge=1, le=MAX_LIMIT)] = DEFAULT_LIMIT,
    cursor: str | None = None,
) -> Page[PostOut]:
    return await studio.list_posts(db, principal, status=post_status, limit=limit, offset=decode_cursor(cursor))


@router.get("/{post_id}", response_model=PostOut)
async def get_post(post_id: UUID, principal: Manager, db: TenantDb) -> PostOut:
    return await studio.get_post(db, principal, post_id)


@router.patch("/{post_id}", response_model=PostOut)
async def update_post(post_id: UUID, body: PostUpdate, principal: Manager, db: TenantDb) -> PostOut:
    return await studio.update_post(db, principal, post_id, body)


@router.post("/{post_id}/submit", response_model=PostOut)
async def submit_post(post_id: UUID, principal: Manager, db: TenantDb) -> PostOut:
    return await studio.submit_for_approval(db, principal, post_id)


@router.delete("/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
async def archive_post(post_id: UUID, principal: Manager, db: TenantDb) -> Response:
    await studio.archive_post(db, principal, post_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
