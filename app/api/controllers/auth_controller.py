"""Auth endpoints: register (account + first shop), login, me, switch-tenant (PRD F-001, F-002, §14)."""

from __future__ import annotations

import re
import secrets
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.core.auth import ALL_ROLES, public_route, require_role
from app.core.security import create_access_token, hash_password, verify_password
from app.core.tenancy import Principal, anonymous_session, apply_context
from app.models.tenant import AuditLog, Membership, Tenant, TenantRole
from app.models.user import User
from app.schemas.user import (
    LoginRequest,
    MeOut,
    RegisterRequest,
    SwitchTenantRequest,
    TenantMembershipOut,
    TokenOut,
    UserOut,
)

router = APIRouter()

# Verified against when the e-mail is unknown, so response time does not reveal which e-mails exist.
_DUMMY_HASH = hash_password("not-a-real-password")
_INVALID = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")


def _slugify(name: str) -> str:
    base = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")[:60] or "shop"
    return f"{base}-{secrets.token_hex(3)}"


def _mask_email(email: str) -> str:
    local, _, domain = email.partition("@")
    return f"{local[:1]}***@{domain}"


def _token_for(user: User, tenant_id: uuid.UUID, role: TenantRole) -> TokenOut:
    token = create_access_token(
        str(user.id),
        extra_claims={"tenant_id": str(tenant_id), "role": role.value, "pa": user.is_platform_admin},
    )
    return TokenOut(access_token=token, tenant_id=tenant_id, role=role)


def _audit(
    action: str,
    *,
    tenant_id: uuid.UUID | None,
    actor_id: uuid.UUID | None,
    entity: str | None = None,
    entity_id: uuid.UUID | None = None,
    after: dict[str, Any] | None = None,
) -> AuditLog:
    return AuditLog(
        tenant_id=tenant_id,
        actor_type="user",
        actor_id=str(actor_id) if actor_id else None,
        action=action,
        entity=entity,
        entity_id=str(entity_id) if entity_id else None,
        after_json=after,
    )


@router.post("/register", response_model=TokenOut, status_code=201, dependencies=[Depends(public_route)])
async def register(body: RegisterRequest) -> TokenOut:
    """Create the user, the tenant and the owner membership in one transaction."""
    if not body.accept_terms:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Terms must be accepted")

    user_id = uuid.uuid4()
    tenant_id = uuid.uuid4()
    email = body.email.lower()
    try:
        async with anonymous_session() as session:
            # The tenants policy is keyed on the row's own id, so the context is set before inserting it.
            await apply_context(session, tenant_id=tenant_id, user_id=user_id)
            existing = await session.execute(select(User.id).where(User.email == email))
            if existing.first() is not None:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")
            user = User(id=user_id, email=email, hashed_password=hash_password(body.password), name=body.full_name)
            session.add(user)
            session.add(
                Tenant(
                    id=tenant_id,
                    name=body.shop_name,
                    slug=_slugify(body.shop_name),
                    owner_phone=body.phone,
                    city=body.city,
                )
            )
            await session.flush()
            session.add(Membership(tenant_id=tenant_id, user_id=user_id, role=TenantRole.owner.value))
            session.add(
                _audit(
                    "tenant.registered",
                    tenant_id=tenant_id,
                    actor_id=user_id,
                    entity="tenant",
                    entity_id=tenant_id,
                    after={"shop_name": body.shop_name, "email": _mask_email(email)},
                )
            )
    except IntegrityError as exc:  # concurrent registration with the same e-mail
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered") from exc
    return _token_for(user, tenant_id, TenantRole.owner)


@router.post("/login", response_model=TokenOut, dependencies=[Depends(public_route)])
async def login(body: LoginRequest) -> TokenOut:
    """Verify credentials, pick the tenant, return a token carrying ``tenant_id`` and ``role``."""
    email = body.email.lower()
    failure: HTTPException | None = None
    token: TokenOut | None = None

    async with anonymous_session() as session:
        user = (await session.execute(select(User).where(User.email == email))).scalar_one_or_none()
        valid = verify_password(body.password, user.hashed_password if user else _DUMMY_HASH)
        if user is None or not valid or not user.is_active:
            session.add(_audit("auth.login_failed", tenant_id=None, actor_id=None, after={"email": _mask_email(email)}))
            failure = _INVALID
        else:
            await apply_context(session, user_id=user.id)
            rows = (
                await session.execute(
                    select(Membership.tenant_id, Membership.role, Tenant.name)
                    .join(Tenant, Tenant.id == Membership.tenant_id)
                    .where(Membership.user_id == user.id)
                    .order_by(Tenant.name)
                )
            ).all()
            chosen = None
            if body.tenant_id is not None:
                chosen = next((r for r in rows if r.tenant_id == body.tenant_id), None)
                if chosen is None:
                    failure = HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a member of that tenant")
            elif len(rows) == 1:
                chosen = rows[0]
            elif len(rows) > 1:
                failure = HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail={
                        "code": "tenant_required",
                        "tenants": [{"tenant_id": str(r.tenant_id), "tenant_name": r.name} for r in rows],
                    },
                )
            else:
                failure = HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No tenant for this account")
            if chosen is not None:
                await apply_context(session, tenant_id=chosen.tenant_id)
                session.add(_audit("auth.login", tenant_id=chosen.tenant_id, actor_id=user.id))
                token = _token_for(user, chosen.tenant_id, TenantRole(chosen.role))

    if failure is not None:
        raise failure
    assert token is not None
    return token


@router.get("/me", response_model=MeOut)
async def me(principal: Principal = Depends(require_role(*ALL_ROLES))) -> MeOut:
    async with anonymous_session(user_id=principal.user_id) as session:
        user = (await session.execute(select(User).where(User.id == principal.user_id))).scalar_one_or_none()
        if user is None or not user.is_active:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
        rows = (
            await session.execute(
                select(Membership.tenant_id, Membership.role, Tenant.name)
                .join(Tenant, Tenant.id == Membership.tenant_id)
                .where(Membership.user_id == principal.user_id)
                .order_by(Tenant.name)
            )
        ).all()
        return MeOut(
            user=UserOut.model_validate(user),
            tenant_id=principal.tenant_id,
            role=principal.role,
            memberships=[
                TenantMembershipOut(tenant_id=r.tenant_id, tenant_name=r.name, role=TenantRole(r.role)) for r in rows
            ],
        )


@router.post("/switch-tenant", response_model=TokenOut)
async def switch_tenant(
    body: SwitchTenantRequest, principal: Principal = Depends(require_role(*ALL_ROLES))
) -> TokenOut:
    """Issue a new token for another tenant the caller belongs to."""
    async with anonymous_session(user_id=principal.user_id) as session:
        user = (await session.execute(select(User).where(User.id == principal.user_id))).scalar_one_or_none()
        membership = (
            await session.execute(
                select(Membership.role).where(
                    Membership.user_id == principal.user_id, Membership.tenant_id == body.tenant_id
                )
            )
        ).first()
        if user is None or not user.is_active or membership is None:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a member of that tenant")
        await apply_context(session, tenant_id=body.tenant_id)
        session.add(_audit("auth.switch_tenant", tenant_id=body.tenant_id, actor_id=user.id))
        return _token_for(user, body.tenant_id, TenantRole(membership.role))
