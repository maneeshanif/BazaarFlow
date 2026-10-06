from fastapi import APIRouter

from app.api.controllers.voice_controller import router as ep

router = APIRouter(prefix="/voice", tags=["voice"])
router.include_router(ep)
