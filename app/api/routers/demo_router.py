from fastapi import APIRouter

from app.api.controllers.demo_controller import router as ep

router = APIRouter(prefix="/demo", tags=["demo"])
router.include_router(ep)
