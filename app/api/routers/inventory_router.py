from app.api.controllers.inventory_controller import router as ep
from fastapi import APIRouter
router = APIRouter(prefix="/api/inventory", tags=["inventory"])
router.include_router(ep)
