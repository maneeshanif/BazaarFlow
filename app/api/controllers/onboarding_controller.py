"""Onboarding wizard API (PRD F-003): owner only."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import OWNER_ONLY, get_tenant_db, require_role
from app.core.tenancy import Principal
from app.schemas.onboarding import ImportReport, ImportRequest, OnboardingOut, ShopStep, TestMessageResult
from app.services import onboarding_service

router = APIRouter()

TenantDb = Annotated[AsyncSession, Depends(get_tenant_db, scope="function")]
Owner = Annotated[Principal, Depends(require_role(*OWNER_ONLY))]


@router.get("/", response_model=OnboardingOut)
async def get_state(principal: Owner, db: TenantDb) -> OnboardingOut:
    return await onboarding_service.get_state(db, principal)


@router.put("/shop", response_model=OnboardingOut)
async def save_shop(body: ShopStep, principal: Owner, db: TenantDb) -> OnboardingOut:
    """Step 1 (required): the shop's name, the owner's phone and the city."""
    return await onboarding_service.save_shop(db, principal, body)


@router.post("/channels/continue", response_model=OnboardingOut)
async def finish_channels(principal: Owner, db: TenantDb) -> OnboardingOut:
    """Step 2 is done when the owner moves on: WhatsApp and Facebook connected, or skipped."""
    return await onboarding_service.finish_channels(db, principal)


@router.post("/products/import", response_model=ImportReport)
async def import_products(body: ImportRequest, principal: Owner, db: TenantDb) -> ImportReport:
    """Step 3: import a CSV. Valid rows are imported; each bad row is listed with its line and reason."""
    return await onboarding_service.import_products(db, principal, body.csv)


@router.post("/products/continue", response_model=OnboardingOut)
async def finish_products(principal: Owner, db: TenantDb) -> OnboardingOut:
    return await onboarding_service.finish_products(db, principal)


@router.post("/test-message", response_model=TestMessageResult)
async def test_message(principal: Owner, db: TenantDb) -> TestMessageResult:
    """Step 4: a WhatsApp test to the owner's phone. A success makes the shop live; a failure explains itself."""
    return await onboarding_service.send_test_message(db, principal)


@router.post("/finish", response_model=OnboardingOut)
async def finish(principal: Owner, db: TenantDb) -> OnboardingOut:
    """Finish without a test message."""
    return await onboarding_service.go_live(db, principal)
