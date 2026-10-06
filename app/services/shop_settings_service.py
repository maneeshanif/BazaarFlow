"""Shop profile and settings (PRD F-020): the owner reads and edits their own shop; every change is audited.

The sales agent reads the shop's auto-post limit through ``effective_auto_post_limit``: the shop's own value when the
owner set one, the platform default otherwise (PKR 0, so every AI write waits for approval).
"""

from __future__ import annotations

import uuid
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import record_audit
from app.core.problems import DomainError, NotFound
from app.core.settings import settings
from app.core.tenancy import Principal
from app.models.tenant import Tenant
from app.schemas.shop import ShopSettingsOut, ShopSettingsUpdate

ZERO = Decimal("0.00")
_EDITABLE = ("name", "owner_phone", "city", "auto_post_limit")


async def _tenant(db: AsyncSession, tenant_id: uuid.UUID) -> Tenant:
    row = (await db.execute(select(Tenant).where(Tenant.id == tenant_id))).scalar_one_or_none()
    if row is None:
        raise NotFound("Shop")
    return row


def _effective(limit: Decimal | None) -> Decimal:
    return Decimal(limit if limit is not None else settings.AGENT_AUTO_POST_LIMIT).quantize(ZERO)


async def effective_auto_post_limit(db: AsyncSession, tenant_id: uuid.UUID) -> Decimal:
    """The largest sale the AI may post on its own for this shop (0 means it always asks)."""
    own = (await db.execute(select(Tenant.auto_post_limit).where(Tenant.id == tenant_id))).scalar_one_or_none()
    return _effective(own)


def _out(tenant: Tenant) -> ShopSettingsOut:
    return ShopSettingsOut(
        id=tenant.id,
        name=tenant.name,
        slug=tenant.slug,
        plan=tenant.plan,
        currency=tenant.currency,
        timezone=tenant.timezone,
        owner_phone=tenant.owner_phone,
        city=tenant.city,
        onboarding_state=tenant.onboarding_state,
        agents_enabled=tenant.agents_enabled,
        agent_cap_usd=tenant.agent_cap_usd,
        auto_post_limit=tenant.auto_post_limit,
        effective_auto_post_limit=_effective(tenant.auto_post_limit),
        created_at=tenant.created_at,
        updated_at=tenant.updated_at,
    )


async def get_shop(db: AsyncSession, principal: Principal) -> ShopSettingsOut:
    return _out(await _tenant(db, principal.tenant_id))


async def update_shop(db: AsyncSession, principal: Principal, body: ShopSettingsUpdate) -> ShopSettingsOut:
    changes = body.model_dump(exclude_unset=True)
    if not changes:
        raise DomainError("Nothing to update", code="empty_update")
    if changes.get("name") is None and "name" in changes:
        raise DomainError("A shop needs a name", code="name_required")
    tenant = await _tenant(db, principal.tenant_id)
    before = {k: getattr(tenant, k) for k in changes if k in _EDITABLE}
    for field, value in changes.items():
        setattr(tenant, field, value)
    await db.flush()
    record_audit(
        db,
        "shop.updated",
        tenant_id=principal.tenant_id,
        actor_id=principal.user_id,
        entity="tenant",
        entity_id=principal.tenant_id,
        before={k: str(v) if isinstance(v, Decimal) else v for k, v in before.items()},
        after={k: str(v) if isinstance(v, Decimal) else v for k, v in changes.items()},
    )
    await db.refresh(tenant)
    return _out(tenant)
