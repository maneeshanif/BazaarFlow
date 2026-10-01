from fastapi import APIRouter, Depends

from app.api.controllers.logs_controller import router as ep
from app.core.auth import require_platform_admin

router = APIRouter(prefix="/api/logs", tags=["logs"], dependencies=[Depends(require_platform_admin)])
router.include_router(ep)
