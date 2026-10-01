from fastapi import APIRouter, Depends

from app.api.controllers.inventory_controller import router as ep
from app.core.auth import ALL_ROLES, require_role

router = APIRouter(prefix="/api/inventory", tags=["inventory"], dependencies=[Depends(require_role(*ALL_ROLES))])
router.include_router(ep)
