from app.api.controllers.support_controller import router as ep
from fastapi import APIRouter
router = APIRouter(tags=["support"])
router.include_router(ep)
