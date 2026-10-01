from fastapi import APIRouter

from app.api.controllers.webhook_controller import router as ep

router = APIRouter(tags=["webhook"])
router.include_router(ep)
