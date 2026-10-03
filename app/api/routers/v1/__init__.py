"""API v1 router aggregate.

Only routers that are really versioned live here (auth, customers, inventory, sales, orders, team, chat, approvals, agent-runs). The legacy JSON-backed routers
keep their ``/api/...`` paths until each module moves to the database and gets a v1 router.
"""

from fastapi import APIRouter

from app.api.routers.agent_router import approvals_router, chat_router, runs_router
from app.api.routers.auth_router import router as auth_router
from app.api.routers.customers_router import router as customers_router
from app.api.routers.inventory_router import router as inventory_router
from app.api.routers.sales_router import orders_router, sales_router
from app.api.routers.team_router import router as team_router

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
