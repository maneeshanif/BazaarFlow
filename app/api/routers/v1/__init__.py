"""API v1 router aggregate."""
from fastapi import APIRouter

from app.api.routers.auth_router import router as auth_router
from app.api.routers.vendors_router import router as vendors_router
from app.api.routers.sales_router import router as sales_router
from app.api.routers.chat_router import router as chat_router
from app.api.routers.inventory_router import router as inventory_router
from app.api.routers.marketing_router import router as marketing_router
from app.api.routers.support_router import router as support_router
from app.api.routers.logs_router import router as logs_router

api_v1_router = APIRouter(prefix="/api/v1")

api_v1_router.include_router(auth_router)
api_v1_router.include_router(vendors_router)
api_v1_router.include_router(sales_router)
api_v1_router.include_router(chat_router)
api_v1_router.include_router(inventory_router)
api_v1_router.include_router(marketing_router)
api_v1_router.include_router(support_router)
api_v1_router.include_router(logs_router)
