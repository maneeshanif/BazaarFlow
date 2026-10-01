"""Auth endpoints: register, login, refresh, logout, me, switch-tenant (PRD F-001, F-002, §14)."""

from __future__ import annotations

import hashlib
import re
import secrets
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import refresh_tokens
from app.core.audit import mask_email, record_audit
from app.core.auth import ALL_ROLES, public_route, require_role
from app.core.security import create_access_token, hash_password, verify_password
from app.core.settings import settings
from app.core.tenancy import Principal, anonymous_session, apply_context
from app.models.security import LoginAttempt
from app.models.tenant import Membership, Tenant, TenantRole
from app.models.user import User
from app.schemas.user import (
    LoginRequest,
    MeOut,
    RefreshRequest,
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


def _email_hash(email: str) -> str:
    return hashlib.sha256(email.encode("utf-8")).hexdigest()


async def _tokens(session: AsyncSession, user: User, tenant_id: uuid.UUID, role: TenantRole) -> TokenOut:
    """Access token (tenant + role claims) plus a fresh refresh token for the same session."""
    access = create_access_token(
        str(user.id),
        extra_claims={"tenant_id": str(tenant_id), "role": role.value, "pa": user.is_platform_admin},
    )
    refresh = await refresh_tokens.issue(session, user.id, tenant_id)
    return TokenOut(access_token=access, refresh_token=refresh, tenant_id=tenant_id, role=role)


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
            if (await session.execute(select(User.id).where(User.email == email))).first() is not None:
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
            record_audit(
                session,
                "tenant.registered",
                tenant_id=tenant_id,
                actor_id=user_id,
                entity="tenant",
                entity_id=tenant_id,
                after={"shop_name": body.shop_name, "email": mask_email(email)},
            )
            return await _tokens(session, user, tenant_id, TenantRole.owner)
    except IntegrityError as exc:  # concurrent registration with the same e-mail
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered") from exc


@router.post("/login", response_model=TokenOut, dependencies=[Depends(public_route)])
async def login(body: LoginRequest) -> TokenOut:
    """Verify credentials, pick the tenant, return tokens carrying ``tenant_id`` and ``role``."""
    email = body.email.lower()
    email_hash = _email_hash(email)
    failure: HTTPException | None = None
    result: TokenOut | None = None
    window_start = datetime.now(timezone.utc) - timedelta(minutes=settings.LOGIN_LOCKOUT_MINUTES)

    async with anonymous_session() as session:
        recent_failures = (
            await session.execute(
                select(func.count())
                .select_from(LoginAttempt)
                .where(
                    LoginAttempt.email_hash == email_hash,
                    LoginAttempt.succeeded.is_(False),
                    LoginAttempt.created_at > window_start,
                )
            )
        ).scalar_one()
        if recent_failures >= settings.LOGIN_MAX_FAILURES:
            failure = HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many failed attempts; try again later",
                headers={"Retry-After": str(settings.LOGIN_LOCKOUT_MINUTES * 60)},
            )
        else:
            user = (await session.execute(select(User).where(User.email == email))).scalar_one_or_none()
            valid = verify_password(body.password, user.hashed_password if user else _DUMMY_HASH)
            if user is None or not valid or not user.is_active:
                session.add(LoginAttempt(email_hash=email_hash, succeeded=False))
                record_audit(session, "auth.login_failed", tenant_id=None, after={"email": mask_email(email)})
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
                        failure = HTTPException(status.HTTP_403_FORBIDDEN, "Not a member of that tenant")
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
                    failure = HTTPException(status.HTTP_403_FORBIDDEN, "No tenant for this account")
                if chosen is not None:
                    await session.execute(
                        delete(LoginAttempt).where(LoginAttempt.email_hash == email_hash, LoginAttempt.succeeded.is_(False))
                    )
                    await apply_context(session, tenant_id=chosen.tenant_id)
                    record_audit(session, "auth.login", tenant_id=chosen.tenant_id, actor_id=user.id)
                    result = await _tokens(session, user, chosen.tenant_id, TenantRole(chosen.role))

    if failure is not None:
        raise failure
    assert result is not None
    return result


@router.post("/refresh", response_model=TokenOut, dependencies=[Depends(public_route)])
async def refresh(body: RefreshRequest) -> TokenOut:
    """Rotate a refresh token and issue a new access token with the membership's *current* role."""
    failure: HTTPException | None = None
    result: TokenOut | None = None
    async with anonymous_session() as session:
        try:
            old, new_raw = await refresh_tokens.rotate(session, body.refresh_token)
        except refresh_tokens.RefreshError:
            failure = HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid refresh token")
        else:
            await apply_context(session, user_id=old.user_id)
            user = (await session.execute(select(User).where(User.id == old.user_id))).scalar_one_or_none()
            member = (
                await session.execute(
                    select(Membership.role).where(
                        Membership.user_id == old.user_id, Membership.tenant_id == old.tenant_id
                    )
                )
            ).first()
            if user is None or not user.is_active or member is None:
                await refresh_tokens.revoke(session, new_raw)
                failure = HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid refresh token")
            else:
                await apply_context(session, tenant_id=old.tenant_id)
                role = TenantRole(member.role)
                access = create_access_token(
                    str(user.id),
                    extra_claims={"tenant_id": str(old.tenant_id), "role": role.value, "pa": user.is_platform_admin},
                )
                record_audit(session, "auth.refresh", tenant_id=old.tenant_id, actor_id=user.id)
                result = TokenOut(access_token=access, refresh_token=new_raw, tenant_id=old.tenant_id, role=role)
    if failure is not None:
        raise failure
    assert result is not None
    return result


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(public_route)])
async def logout(body: RefreshRequest) -> Response:
    """Revoke the session's refresh token. Idempotent: an unknown token is not an error."""
    async with anonymous_session() as session:
        row = await refresh_tokens.revoke(session, body.refresh_token)
        if row is not None:
            await apply_context(session, tenant_id=row.tenant_id)
            record_audit(session, "auth.logout", tenant_id=row.tenant_id, actor_id=row.user_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


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
    """Issue tokens for another tenant the caller belongs to."""
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
        record_audit(session, "auth.switch_tenant", tenant_id=body.tenant_id, actor_id=user.id)
        return await _tokens(session, user, body.tenant_id, TenantRole(membership.role))
