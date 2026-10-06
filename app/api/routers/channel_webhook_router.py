from fastapi import APIRouter

from app.api.controllers.channel_webhook_controller import router as ep

router = APIRouter(prefix="/webhooks", tags=["webhooks"])
router.include_router(ep)
