from app.api.controllers.webhook_controller import router as ep
from fastapi import APIRouter
router = APIRouter(tags=["webhook"])
router.include_router(ep)
