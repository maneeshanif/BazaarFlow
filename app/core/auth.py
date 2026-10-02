"""Authentication and authorization dependencies (PRD §14, §3.7 constraint 3).

Every route must carry exactly one *authorization decision*: either ``public`` or a role gate built
with ``require_role``. Each decision callable has an ``__authz__`` attribute so the architecture
test can enumerate the router and fail on any route without one.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator, Awaitable, Callable
from typing import Any

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import verify_token
from app.core.tenancy import Principal, anonymous_session, tenant_session
from app.models.tenant import Membership, TenantRole
from app.models.user import User

_bearer = HTTPBearer(auto_error=False)

ALL_ROLES: tuple[TenantRole, ...] = (TenantRole.owner, TenantRole.manager, TenantRole.staff)
MANAGER_UP: tuple[TenantRole, ...] = (TenantRole.owner, TenantRole.manager)
OWNER_ONLY: tuple[TenantRole, ...] = (TenantRole.owner,)

_UNAUTHENTICATED = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Not authenticated",
    headers={"WWW-Authenticate": "Bearer"},
)


def public_route() -> None:
    """Marker dependency: the route is deliberately reachable without authentication."""


public_route.__authz__ = "public"  # type: ignore[attr-defined]


def _principal_from_claims(claims: dict[str, Any]) -> Principal:
    try:
        return Principal(
            user_id=uuid.UUID(str(claims["sub"])),
            tenant_id=uuid.UUID(str(claims["tenant_id"])),
            role=TenantRole(claims["role"]),
            is_platform_admin=bool(claims.get("pa", False)),
        )
    except (KeyError, ValueError) as exc:
        raise _UNAUTHENTICATED from exc


async def get_principal(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> Principal:
    """Decode the bearer token into a Principal; 401 when missing, invalid or expired."""
    if credentials is None:
        raise _UNAUTHENTICATED
    try:
        claims = verify_token(credentials.credentials)
    except jwt.PyJWTError as exc:
        raise _UNAUTHENTICATED from exc
    principal = _principal_from_claims(claims)
    await _confirm_still_valid(principal)
    return principal


async def _confirm_still_valid(principal: Principal) -> None:
    """The token can be up to ACCESS_TOKEN_EXPIRE_MINUTES old: confirm the database still agrees.

    A deactivated user, a removed or demoted member, or a platform-admin flag that was withdrawn all lose access on
    the very next request, on every route (they must refresh to get a token that reflects the new state).
    """
    async with anonymous_session(user_id=principal.user_id) as session:
        row = (
            await session.execute(
                select(Membership.role, User.is_active, User.is_platform_admin)
                .join(User, User.id == Membership.user_id)
                .where(Membership.user_id == principal.user_id, Membership.tenant_id == principal.tenant_id)
            )
        ).first()
    if (
        row is None
        or not row.is_active
        or row.role != principal.role.value
        or bool(row.is_platform_admin) != principal.is_platform_admin
    ):
        raise _UNAUTHENTICATED


def require_role(*roles: TenantRole) -> Callable[..., Awaitable[Principal]]:
    """Build a dependency that admits only the given tenant roles (403 otherwise)."""
    allowed = frozenset(roles or ALL_ROLES)

    async def _check(principal: Principal = Depends(get_principal)) -> Principal:
        if principal.role not in allowed:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")
        return principal

    _check.__authz__ = tuple(sorted(r.value for r in allowed))  # type: ignore[attr-defined]
    return _check


async def require_platform_admin(principal: Principal = Depends(get_principal)) -> Principal:
    """Admit BazaarFlow operators only (the ``is_platform_admin`` flag, carried in the token)."""
    if not principal.is_platform_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Platform admin only")
    return principal


require_platform_admin.__authz__ = ("platform_admin",)  # type: ignore[attr-defined]


async def get_tenant_db(principal: Principal = Depends(get_principal)) -> AsyncIterator[AsyncSession]:
    """A session whose transaction is scoped to the caller's tenant (RLS applies).

    Use it as ``Depends(get_tenant_db, scope="function")`` so the transaction commits before the response is
    sent; an architecture test enforces this.
    """
    async with tenant_session(principal.tenant_id, principal.user_id) as session:
        yield session
