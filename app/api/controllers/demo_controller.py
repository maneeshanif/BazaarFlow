"""Public live demo API (PRD F-027): start a temporary shop and get its owner's session."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.core.auth import public_route
from app.core.problems import DomainError
from app.core.settings import settings
from app.core.throttle import demo_throttle
from app.schemas.user import TokenOut
from app.services import demo_service

router = APIRouter()


@router.post(
    "/start", response_model=TokenOut, status_code=201, dependencies=[Depends(public_route), Depends(demo_throttle)]
)
async def start_demo() -> TokenOut:
    if not settings.DEMO_ENABLED:
        raise DomainError("The live demo is switched off right now.", code="demo_disabled", status_code=404)
    return await demo_service.start()
