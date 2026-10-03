"""One place that mints a session: the access token (tenant and role claims) plus a fresh refresh token."""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core import refresh_tokens
from app.core.security import create_access_token
from app.models.tenant import TenantRole
from app.models.user import User
from app.schemas.user import TokenOut


async def issue_tokens(session: AsyncSession, user: User, tenant_id: uuid.UUID, role: TenantRole) -> TokenOut:
    access = create_access_token(
        str(user.id),
        extra_claims={"tenant_id": str(tenant_id), "role": role.value, "pa": user.is_platform_admin},
    )
    refresh = await refresh_tokens.issue(session, user.id, tenant_id)
    return TokenOut(access_token=access, refresh_token=refresh, tenant_id=tenant_id, role=role)
