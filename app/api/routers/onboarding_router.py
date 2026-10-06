from fastapi import APIRouter

from app.api.controllers.onboarding_controller import router as ep

router = APIRouter(prefix="/onboarding", tags=["onboarding"])
router.include_router(ep)
