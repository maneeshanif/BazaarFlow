"""Shop profile and settings API (PRD F-020): owner only."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import OWNER_ONLY, get_tenant_db, require_role
from app.core.tenancy import Principal
from app.schemas.shop import ShopSettingsOut, ShopSettingsUpdate
from app.services import shop_settings_service

router = APIRouter()

TenantDb = Annotated[AsyncSession, Depends(get_tenant_db, scope="function")]


@router.get("/shop", response_model=ShopSettingsOut)
async def get_shop(principal: Annotated[Principal, Depends(require_role(*OWNER_ONLY))], db: TenantDb) -> ShopSettingsOut:
    return await shop_settings_service.get_shop(db, principal)


@router.patch("/shop", response_model=ShopSettingsOut)
async def update_shop(
    body: ShopSettingsUpdate, principal: Annotated[Principal, Depends(require_role(*OWNER_ONLY))], db: TenantDb
) -> ShopSettingsOut:
    return await shop_settings_service.update_shop(db, principal, body)
