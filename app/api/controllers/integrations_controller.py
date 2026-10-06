"""Integrations API (PRD F-018): owner only. Credentials go in, never out."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import OWNER_ONLY, get_tenant_db, require_role
from app.core.tenancy import Principal
from app.schemas.integrations import PROVIDERS, ConnectRequest, IntegrationOut
from app.services import integration_service

router = APIRouter()

TenantDb = Annotated[AsyncSession, Depends(get_tenant_db, scope="function")]
Owner = Annotated[Principal, Depends(require_role(*OWNER_ONLY))]


def _provider(provider: Annotated[str, Path(max_length=30)]) -> str:
    if provider not in PROVIDERS:
        raise HTTPException(status_code=404, detail="Unknown integration")
    return provider


Provider = Annotated[str, Depends(_provider)]


@router.get("/", response_model=list[IntegrationOut])
async def list_integrations(principal: Owner, db: TenantDb) -> list[IntegrationOut]:
    return await integration_service.list_integrations(db, principal)


@router.put("/{provider}", response_model=IntegrationOut)
async def connect_integration(provider: Provider, body: ConnectRequest, principal: Owner, db: TenantDb) -> IntegrationOut:
    """Check the credentials with the provider, then save them encrypted. The answer never contains them."""
    return await integration_service.connect(db, principal, provider, body.credentials)


@router.delete("/{provider}", response_model=IntegrationOut)
async def disconnect_integration(provider: Provider, principal: Owner, db: TenantDb) -> IntegrationOut:
    return await integration_service.disconnect(db, principal, provider)
