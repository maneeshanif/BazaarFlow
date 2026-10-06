from fastapi import APIRouter

from app.api.controllers.platform_controller import router as ep

router = APIRouter(prefix="/platform", tags=["platform"])
router.include_router(ep)
