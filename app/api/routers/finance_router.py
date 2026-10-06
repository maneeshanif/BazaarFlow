from fastapi import APIRouter

from app.api.controllers.finance_controller import router as ep

router = APIRouter(prefix="/finance", tags=["finance"])
router.include_router(ep)
