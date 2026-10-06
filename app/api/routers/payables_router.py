from fastapi import APIRouter

from app.api.controllers.payables_controller import router as ep

router = APIRouter(prefix="/vendors", tags=["vendors"])
router.include_router(ep)
