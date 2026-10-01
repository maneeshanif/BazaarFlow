from fastapi import APIRouter

from app.api.controllers.support_controller import router as ep

router = APIRouter(tags=["support"])
router.include_router(ep)
