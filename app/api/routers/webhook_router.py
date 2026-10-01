from fastapi import APIRouter, Depends

from app.api.controllers.webhook_controller import router as ep
from app.core.auth import public_route

router = APIRouter(tags=["webhook"], dependencies=[Depends(public_route)])
router.include_router(ep)
