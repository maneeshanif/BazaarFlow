from fastapi import APIRouter

from app.api.controllers.auth_controller import router as ep

router = APIRouter(prefix="/auth", tags=["auth"])
router.include_router(ep)
