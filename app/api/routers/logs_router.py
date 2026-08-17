from app.api.controllers.logs_controller import router as ep
from fastapi import APIRouter
router = APIRouter(prefix="/api/logs", tags=["logs"])
router.include_router(ep)
