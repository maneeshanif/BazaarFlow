"""API v1 router aggregate.

Only routers that are really versioned live here (auth, customers, inventory, sales, orders, team, chat, approvals, agent-runs, marketing, dashboard, demo). The legacy JSON-backed routers
keep their ``/api/...`` paths until each module moves to the database and gets a v1 router.
"""

from fastapi import APIRouter

from app.api.routers.agent_router import approvals_router, chat_router, runs_router
from app.api.routers.auth_router import router as auth_router
from app.api.routers.automations_router import router as automations_router
from app.api.routers.channel_webhook_router import router as channel_webhook_router
from app.api.routers.customers_router import router as customers_router
from app.api.routers.dashboard_router import router as dashboard_router
from app.api.routers.demo_router import router as demo_router
from app.api.routers.finance_router import router as finance_router
from app.api.routers.inbox_router import router as inbox_router
from app.api.routers.integrations_router import router as integrations_router
from app.api.routers.inventory_router import router as inventory_router
from app.api.routers.marketing_schedule_router import router as marketing_schedule_router
from app.api.routers.marketing_studio_router import router as marketing_studio_router
from app.api.routers.onboarding_router import router as onboarding_router
from app.api.routers.payables_router import router as payables_router
from app.api.routers.platform_router import router as platform_router
from app.api.routers.sales_router import orders_router, sales_router
from app.api.routers.settings_router import router as settings_router
from app.api.routers.team_router import router as team_router
from app.api.routers.voice_router import router as voice_router

api_v1_router = APIRouter(prefix="/api/v1")

api_v1_router.include_router(auth_router)
api_v1_router.include_router(customers_router)
api_v1_router.include_router(inventory_router)
api_v1_router.include_router(sales_router)
api_v1_router.include_router(orders_router)
api_v1_router.include_router(team_router)
api_v1_router.include_router(chat_router)
api_v1_router.include_router(approvals_router)
api_v1_router.include_router(runs_router)
api_v1_router.include_router(marketing_studio_router)
api_v1_router.include_router(dashboard_router)
api_v1_router.include_router(demo_router)
api_v1_router.include_router(payables_router)
api_v1_router.include_router(settings_router)
api_v1_router.include_router(finance_router)
api_v1_router.include_router(platform_router)
for _r in (voice_router, automations_router, channel_webhook_router, inbox_router, integrations_router, marketing_schedule_router, onboarding_router):
    api_v1_router.include_router(_r)
