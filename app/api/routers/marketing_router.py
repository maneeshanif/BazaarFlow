from fastapi import APIRouter, Depends

from app.api.controllers.marketing_controller import router as ep
from app.core.auth import MANAGER_UP, require_role

router = APIRouter(prefix="/api/marketing", tags=["marketing"], dependencies=[Depends(require_role(*MANAGER_UP))])
router.include_router(ep)
