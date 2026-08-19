"""Sales endpoints � exact port of backend/controllers/sales_controller.py"""
from __future__ import annotations
from typing import Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

router = APIRouter()


class SalesForm(BaseModel):
    customer_name: str = Field(..., description="Full name of the customer")
    customer_phone: str = Field(..., description="Customer WhatsApp or phone number")
    product_id: str = Field(..., description="Product SKU or internal ID")
    product_name: Optional[str] = Field(None, description="Readable product name")
    quantity: int = Field(..., gt=0, description="Quantity ordered")
    budget: Optional[str] = Field(None, description="Expected spending range")
    payment_status: Optional[str] = Field("pending", description="Payment status")
    delivery_address: Optional[str] = Field(None, description="Delivery location")
    notes: Optional[str] = Field(None, description="Extra delivery instructions")


@router.post("/", response_class=JSONResponse)
async def create_sales_order(form: SalesForm):
    try:
        # TODO: delegate to app.services.sales_service.save_order
        return JSONResponse(status_code=201, content={"ok": True, "order": form.model_dump()})
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/", response_class=JSONResponse)
async def get_sales_orders():
    # TODO: delegate to app.services.sales_service.list_orders
    return JSONResponse(status_code=200, content={"ok": True, "orders": []})
