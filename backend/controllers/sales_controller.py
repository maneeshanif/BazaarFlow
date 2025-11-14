from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from ..models.sales_model import SalesForm
from ..services.sales_service import save_order, list_orders
 

router = APIRouter()


@router.post("/sales", response_class=JSONResponse)
async def create_sales_order(form: SalesForm):
    try:
        record = save_order(form.dict())
        return JSONResponse(status_code=201, content={"ok": True, "order": record})
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sales", response_class=JSONResponse)
async def get_sales_orders():
    items = list_orders()
    return JSONResponse(status_code=200, content={"ok": True, "orders": items})
