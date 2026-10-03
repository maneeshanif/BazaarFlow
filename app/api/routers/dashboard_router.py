from fastapi import APIRouter

from app.api.controllers.dashboard_controller import router as ep

router = APIRouter(prefix="/dashboard", tags=["dashboard"])
router.include_router(ep)
