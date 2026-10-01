from fastapi import APIRouter

from app.api.controllers.vendors_controller import router as ep

router = APIRouter(prefix="/api/vendors", tags=["vendors"])
router.include_router(ep)
