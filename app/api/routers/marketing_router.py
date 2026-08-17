from app.api.controllers.marketing_controller import router as ep
from fastapi import APIRouter
router = APIRouter(prefix="/api/marketing", tags=["marketing"])
router.include_router(ep)
