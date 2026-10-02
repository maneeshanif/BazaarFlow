"""Inventory management API endpoints."""
from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.core.auth import MANAGER_UP, require_role
from app.services.inventory_service import inventory_analytics_service

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
async def get_inventory() -> Any:
    """Get all inventory items."""
    items = inventory_analytics_service.get_all_items()
    return {"ok": True, "items": items}


@router.get("/{sku}")
async def get_inventory_item(sku: str) -> Any:
    """Get a specific inventory item by SKU."""
    item = inventory_analytics_service.get_item_by_sku(sku)
    if not item:
        raise HTTPException(status_code=404, detail=f"Item with SKU {sku} not found")
    return {"ok": True, "item": item}


@router.post("/", status_code=201, dependencies=[Depends(require_role(*MANAGER_UP))])
async def create_inventory_item(item: InventoryItemCreate) -> Any:
    """Create a new inventory item."""
    try:
        created_item = inventory_analytics_service.create_item(item.model_dump())
        return {"ok": True, "item": created_item, "message": "Item created successfully"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create item: {str(e)}")


@router.put("/{sku}", dependencies=[Depends(require_role(*MANAGER_UP))])
async def update_inventory_item(sku: str, item: InventoryItemUpdate) -> Any:
    """Update an existing inventory item."""
    try:
        update_data = {k: v for k, v in item.model_dump().items() if v is not None}
        updated_item = inventory_analytics_service.update_item(sku, update_data)
        if not updated_item:
            raise HTTPException(status_code=404, detail=f"Item with SKU {sku} not found")
        return {"ok": True, "item": updated_item, "message": "Item updated successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update item: {str(e)}")


@router.patch("/{sku}/add-stock", dependencies=[Depends(require_role(*MANAGER_UP))])
async def add_stock_to_item(sku: str, request: AddStockRequest) -> Any:
    """Add stock to an existing inventory item."""
    try:
        if request.quantity <= 0:
            raise HTTPException(status_code=400, detail="Quantity must be positive")
        updated_item = inventory_analytics_service.add_stock(sku, request.quantity)
        if not updated_item:
            raise HTTPException(status_code=404, detail=f"Item with SKU {sku} not found")
        return {
            "ok": True,
            "item": updated_item,
            "message": f"Added {request.quantity} units to stock"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to add stock: {str(e)}")


@router.delete("/{sku}", dependencies=[Depends(require_role(*MANAGER_UP))])
async def delete_inventory_item(sku: str) -> Any:
    """Delete an inventory item by SKU."""
    try:
        deleted_item = inventory_analytics_service.delete_item(sku)
        if not deleted_item:
            raise HTTPException(status_code=404, detail=f"Item with SKU {sku} not found")
        return {
            "ok": True,
            "item": deleted_item,
            "message": "Item deleted successfully",
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete item: {str(e)}")
