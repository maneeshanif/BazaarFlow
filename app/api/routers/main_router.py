"""Main aggregated router - registers all domain routers in one place.

In app/main.py:
    from app.api.routers.main_router import main_router
    app.include_router(main_router)
"""
from fastapi import APIRouter

from app.api.routers.auth_router import router as auth_router
from app.api.routers.webhook_router import router as webhook_router
from app.api.routers.vendors_router import router as vendors_router
from app.api.routers.sales_router import router as sales_router
from app.api.routers.chat_router import router as chat_router
from app.api.routers.inventory_router import router as inventory_router
from app.api.routers.marketing_router import router as marketing_router
from app.api.routers.support_router import router as support_router
from app.api.routers.logs_router import router as logs_router

main_router = APIRouter()

main_router.include_router(auth_router)
main_router.include_router(webhook_router)
main_router.include_router(vendors_router)
main_router.include_router(sales_router)
main_router.include_router(chat_router)
main_router.include_router(inventory_router)
main_router.include_router(marketing_router)
main_router.include_router(support_router)
main_router.include_router(logs_router)