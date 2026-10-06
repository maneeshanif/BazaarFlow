from fastapi import APIRouter

from app.api.controllers.inbox_controller import router as ep

router = APIRouter(prefix="/conversations", tags=["inbox"])
router.include_router(ep)
