from fastapi import APIRouter, Depends

from app.api.controllers.vendors_controller import router as ep
from app.core.auth import MANAGER_UP, require_role

router = APIRouter(prefix="/api/vendors", tags=["vendors"], dependencies=[Depends(require_role(*MANAGER_UP))])
router.include_router(ep)
