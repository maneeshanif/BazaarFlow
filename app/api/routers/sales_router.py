from fastapi import APIRouter

from app.api.controllers.sales_controller import router as ep

router = APIRouter(prefix="/api/sales", tags=["sales"])
router.include_router(ep)
