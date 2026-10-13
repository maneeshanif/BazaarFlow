from fastapi import APIRouter

from app.api.controllers.purchase_orders_controller import router as ep

router = APIRouter(prefix="/purchase-orders", tags=["purchase-orders"])
router.include_router(ep)
