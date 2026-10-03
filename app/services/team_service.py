"""Team and roles (PRD F-019, §14.1): who works in the shop and what they may do. Owner-only.

Rules enforced here: owners are never added, changed or removed through this form (one owner stays in charge),
a person is in a shop once, removing someone ends their sessions in that shop at once, and every change is audited.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import mask_email, record_audit
from app.core.problems import Conflict, DomainError, NotFound
from app.core.security import ahash_password
from app.core.tenancy import Principal
from app.models.security import RefreshToken
from app.models.tenant import Membership, TenantRole
from app.models.user import User
from app.schemas.team import TeamMemberCreate, TeamMemberOut, TeamMemberUpdate


def _out(member: Membership, user: User, principal: Principal, *, new_account: bool = False) -> TeamMemberOut:
    return TeamMemberOut(
        id=member.id,
        user_id=user.id,
        name=user.name,
        email=user.email,
        role=member.role,
        is_active=user.is_active,
        joined_at=member.created_at,
        is_you=user.id == principal.user_id,
        new_account=new_account,
    )


async def list_members(db: AsyncSession, principal: Principal) -> list[TeamMemberOut]:
    rows = (
        await db.execute(
            select(Membership, User)
            .join(User, User.id == Membership.user_id)
            .where(Membership.tenant_id == principal.tenant_id)
            .order_by(Membership.role.desc(), User.name, User.email)
        )
    ).all()
    # owners first, then managers, then staff
    order = {TenantRole.owner.value: 0, TenantRole.manager.value: 1, TenantRole.staff.value: 2}
    ranked = sorted(rows, key=lambda r: (order.get(r[0].role, 9), (r[1].name or r[1].email).lower()))
    return [_out(m, u, principal) for m, u in ranked]


async def _get(db: AsyncSession, principal: Principal, membership_id: uuid.UUID) -> tuple[Membership, User]:
    row = (
        await db.execute(
            select(Membership, User)
            .join(User, User.id == Membership.user_id)
            .where(Membership.id == membership_id, Membership.tenant_id == principal.tenant_id)
        )
    ).first()
    if row is None:
        raise NotFound("Team member")
    return row[0], row[1]


async def add_member(db: AsyncSession, principal: Principal, body: TeamMemberCreate) -> TeamMemberOut:
    email = body.email.lower()
    user = (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()
    new_account = user is None
    if user is None:
        if body.password is None:
            raise DomainError(
                "Give them a first password. They can sign in with it straight away.",
                code="password_required",
                status_code=422,
            )
        user = User(id=uuid.uuid4(), email=email, hashed_password=await ahash_password(body.password), name=body.name)
        db.add(user)
        await db.flush()
    elif not user.is_active:
        raise DomainError("That account is switched off and cannot be added", code="account_inactive")
    member = Membership(tenant_id=principal.tenant_id, user_id=user.id, role=body.role)
    try:
        async with db.begin_nested():
            db.add(member)
            await db.flush()
    except IntegrityError as exc:
        raise Conflict(f"{email} is already on your team", code="already_member") from exc
    record_audit(
        db,
        "team.added",
        tenant_id=principal.tenant_id,
        actor_id=principal.user_id,
        entity="membership",
        entity_id=member.id,
        after={"email": mask_email(email), "role": body.role, "new_account": new_account},
    )
    await db.refresh(member)
    return _out(member, user, principal, new_account=new_account)


async def change_role(db: AsyncSession, principal: Principal, membership_id: uuid.UUID, body: TeamMemberUpdate) -> TeamMemberOut:
    member, user = await _get(db, principal, membership_id)
    if member.role == TenantRole.owner.value:
        raise DomainError("The owner's role cannot be changed here", code="owner_is_fixed")
    before = member.role
    member.role = body.role
    await db.flush()
    record_audit(
        db,
        "team.role_changed",
        tenant_id=principal.tenant_id,
        actor_id=principal.user_id,
        entity="membership",
        entity_id=member.id,
        before={"role": before},
        after={"role": body.role, "email": mask_email(user.email)},
    )
    await db.refresh(member)
    return _out(member, user, principal)


async def remove_member(db: AsyncSession, principal: Principal, membership_id: uuid.UUID) -> None:
    member, user = await _get(db, principal, membership_id)
    if member.role == TenantRole.owner.value:
        raise DomainError("The owner cannot be removed from their own shop", code="owner_is_fixed")
    await db.delete(member)
    # their refresh tokens for this shop stop working now; access tokens are re-checked on every request anyway
    await db.execute(
        update(RefreshToken)
        .where(RefreshToken.user_id == user.id, RefreshToken.tenant_id == principal.tenant_id, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=datetime.now(timezone.utc))
    )
    await db.flush()
    record_audit(
        db,
        "team.removed",
        tenant_id=principal.tenant_id,
        actor_id=principal.user_id,
        entity="membership",
        entity_id=member.id,
        before={"role": member.role, "email": mask_email(user.email)},
    )
