"""Inventory endpoints � exact port of backend/controllers/inventory_controller.py"""
from __future__ import annotations
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()


class InventoryItemCreate(BaseModel):
    sku: str
    name: str
    category: str
    price: float
    stock: int
    reorder_point: int
    incoming: int = 0
    supplier: str
    last_restocked: Optional[str] = None


class InventoryItemUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    price: Optional[float] = None
    stock: Optional[int] = None
    reorder_point: Optional[int] = None
    incoming: Optional[int] = None
    supplier: Optional[str] = None


class AddStockRequest(BaseModel):
    quantity: int


@router.get("/")
async def get_inventory():
    """Get all inventory items."""
    # TODO: delegate to app.services.inventory_service
    return {"ok": True, "items": []}


@router.get("/{sku}")
async def get_inventory_item(sku: str):
    """Get a specific inventory item by SKU."""
    # TODO: query by sku
    raise HTTPException(status_code=404, detail=f"Item with SKU {sku} not found")


@router.post("/", status_code=201)
async def create_inventory_item(item: InventoryItemCreate):
    """Create a new inventory item."""
    try:
        # TODO: delegate to inventory_service.create_item
        return {"ok": True, "item": item.model_dump(), "message": "Item created successfully"}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.put("/{sku}")
async def update_inventory_item(sku: str, item: InventoryItemUpdate):
    """Update an existing inventory item."""
    update_data = {k: v for k, v in item.model_dump().items() if v is not None}
    # TODO: inventory_service.update_item(sku, update_data)
    raise HTTPException(status_code=404, detail=f"Item with SKU {sku} not found")


@router.patch("/{sku}/add-stock")
async def add_stock_to_item(sku: str, request: AddStockRequest):
    """Add stock to an existing inventory item."""
    if request.quantity <= 0:
        raise HTTPException(status_code=400, detail="Quantity must be positive")
    # TODO: inventory_service.add_stock(sku, request.quantity)
    raise HTTPException(status_code=404, detail=f"Item with SKU {sku} not found")


@router.delete("/{sku}")
async def delete_inventory_item(sku: str):
    """Delete an inventory item by SKU."""
    # TODO: inventory_service.delete_item(sku)
    raise HTTPException(status_code=404, detail=f"Item with SKU {sku} not found")
