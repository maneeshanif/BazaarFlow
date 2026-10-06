"""Voice API (PRD F-023): the voice agent's settings and calls. Owners edit; managers can read."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import MANAGER_UP, OWNER_ONLY, get_tenant_db, require_role
from app.core.pagination import DEFAULT_LIMIT, MAX_LIMIT, Page, decode_cursor, next_cursor
from app.core.tenancy import Principal
from app.schemas.voice import (
    AssistantConfig,
    CallStatus,
    VoiceCallDetail,
    VoiceCallOut,
    VoiceSettingsIn,
    VoiceSettingsOut,
)
from app.services import voice_service

router = APIRouter()

TenantDb = Annotated[AsyncSession, Depends(get_tenant_db, scope="function")]
Manager = Annotated[Principal, Depends(require_role(*MANAGER_UP))]
Owner = Annotated[Principal, Depends(require_role(*OWNER_ONLY))]


@router.get("/settings", response_model=VoiceSettingsOut)
async def get_settings(principal: Manager, db: TenantDb) -> VoiceSettingsOut:
    return await voice_service.get_settings(db, principal)


@router.put("/settings", response_model=VoiceSettingsOut)
async def put_settings(body: VoiceSettingsIn, principal: Owner, db: TenantDb) -> VoiceSettingsOut:
    return await voice_service.put_settings(db, principal, body)


@router.get("/assistant-config", response_model=AssistantConfig)
async def assistant_config(principal: Owner, db: TenantDb) -> AssistantConfig:
    """The assistant to create in VAPI: consent notice first, interruption, a call-length limit, and the tools this server answers."""
    return await voice_service.assistant_config(db, principal)


@router.get("/calls", response_model=Page[VoiceCallOut])
async def list_calls(
    principal: Manager,
    db: TenantDb,
    status: CallStatus | None = None,
    since: datetime | None = None,
    limit: Annotated[int, Query(ge=1, le=MAX_LIMIT)] = DEFAULT_LIMIT,
    cursor: Annotated[str | None, Query(max_length=60)] = None,
) -> Page[VoiceCallOut]:
    offset = decode_cursor(cursor)
    items, total = await voice_service.list_calls(db, principal, status=status, since=since, limit=limit, offset=offset)
    return Page[VoiceCallOut](items=items, total=total, next_cursor=next_cursor(offset, limit, total))


@router.get("/calls/{call_id}", response_model=VoiceCallDetail)
async def get_call(call_id: UUID, principal: Manager, db: TenantDb) -> VoiceCallDetail:
    return await voice_service.get_call(db, principal, call_id)
