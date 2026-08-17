from app.api.controllers.sales_controller import router as ep
from fastapi import APIRouter
router = APIRouter(prefix="/api/sales", tags=["sales"])
router.include_router(ep)
