from app.api.controllers.vendors_controller import router as ep
from fastapi import APIRouter
router = APIRouter(prefix="/api/vendors", tags=["vendors"])
router.include_router(ep)
