"""Team and roles API (PRD F-019, §13.2): owner only, tenant-scoped, audited."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import OWNER_ONLY, get_tenant_db, require_role
from app.core.tenancy import Principal
from app.schemas.team import TeamMemberCreate, TeamMemberOut, TeamMemberUpdate
from app.services import team_service

router = APIRouter()

TenantDb = Annotated[AsyncSession, Depends(get_tenant_db, scope="function")]
Owner = Annotated[Principal, Depends(require_role(*OWNER_ONLY))]


@router.get("/", response_model=list[TeamMemberOut])
async def list_team(principal: Owner, db: TenantDb) -> list[TeamMemberOut]:
    return await team_service.list_members(db, principal)


@router.post("/", response_model=TeamMemberOut, status_code=status.HTTP_201_CREATED)
async def add_team_member(body: TeamMemberCreate, principal: Owner, db: TenantDb) -> TeamMemberOut:
    return await team_service.add_member(db, principal, body)


@router.patch("/{membership_id}", response_model=TeamMemberOut)
async def change_team_member_role(membership_id: UUID, body: TeamMemberUpdate, principal: Owner, db: TenantDb) -> TeamMemberOut:
    return await team_service.change_role(db, principal, membership_id, body)


@router.delete("/{membership_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_team_member(membership_id: UUID, principal: Owner, db: TenantDb) -> Response:
    await team_service.remove_member(db, principal, membership_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
