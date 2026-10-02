"""Main aggregated router - registers all domain routers in one place.

The legacy v1 routers (inventory, sales, chat, vendors, marketing, logs) are backed by global JSON files that are
shared by every tenant, so they are mounted only where that is safe: always in development and test, never in
production or staging unless ``LEGACY_V1_ROUTES=true`` is set explicitly. Each one is switched off as its module
moves onto the tenant-scoped database (build-plan phase 1).
"""
from fastapi import APIRouter

from app.api.routers.auth_router import router as auth_router
from app.api.routers.chat_router import router as chat_router
from app.api.routers.inventory_router import router as inventory_router
from app.api.routers.logs_router import router as logs_router
from app.api.routers.marketing_router import router as marketing_router
from app.api.routers.sales_router import router as sales_router
from app.api.routers.support_router import router as support_router
from app.api.routers.vendors_router import router as vendors_router
from app.api.routers.webhook_router import router as webhook_router
from app.core.settings import settings


def build_main_router(*, legacy_routes: bool) -> APIRouter:
    router = APIRouter()
    router.include_router(auth_router)
    router.include_router(webhook_router)
    router.include_router(support_router)
    if legacy_routes:
        for legacy in (vendors_router, sales_router, chat_router, inventory_router, marketing_router, logs_router):
            router.include_router(legacy)
    return router


main_router = build_main_router(legacy_routes=settings.legacy_routes_enabled)
