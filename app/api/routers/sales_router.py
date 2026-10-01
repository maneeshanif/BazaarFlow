from fastapi import APIRouter, Depends

from app.api.controllers.sales_controller import router as ep
from app.core.auth import ALL_ROLES, require_role

router = APIRouter(prefix="/api/sales", tags=["sales"], dependencies=[Depends(require_role(*ALL_ROLES))])
router.include_router(ep)
