from fastapi import APIRouter

from app.api.controllers.marketing_schedule_controller import router as ep

router = APIRouter(prefix="/marketing", tags=["marketing"])
router.include_router(ep)
