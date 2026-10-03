from fastapi import APIRouter

from app.api.controllers.orders_controller import orders_router as orders_ep
from app.api.controllers.orders_controller import sales_router as sales_ep

sales_router = APIRouter(prefix="/sales", tags=["sales"])
sales_router.include_router(sales_ep)

orders_router = APIRouter(prefix="/orders", tags=["orders"])
orders_router.include_router(orders_ep)
