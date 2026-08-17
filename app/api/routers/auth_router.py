from app.api.controllers.auth_controller import router as ep
from fastapi import APIRouter
router = APIRouter(prefix="/auth", tags=["auth"])
router.include_router(ep)
