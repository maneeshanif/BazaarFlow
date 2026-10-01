from fastapi import APIRouter

from app.api.controllers.marketing_controller import router as ep

router = APIRouter(prefix="/api/marketing", tags=["marketing"])
router.include_router(ep)
