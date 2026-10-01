from fastapi import APIRouter

from app.api.controllers.inventory_controller import router as ep

router = APIRouter(prefix="/api/inventory", tags=["inventory"])
router.include_router(ep)
