from fastapi import APIRouter

from app.api.controllers.shop_settings_controller import router as ep

router = APIRouter(prefix="/settings", tags=["settings"])
router.include_router(ep)
