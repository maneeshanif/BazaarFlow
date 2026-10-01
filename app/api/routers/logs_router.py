from fastapi import APIRouter

from app.api.controllers.logs_controller import router as ep

router = APIRouter(prefix="/api/logs", tags=["logs"])
router.include_router(ep)
