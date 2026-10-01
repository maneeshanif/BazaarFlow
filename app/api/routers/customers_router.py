from fastapi import APIRouter

from app.api.controllers.customers_controller import router as ep

router = APIRouter(prefix="/customers", tags=["customers"])
router.include_router(ep)
