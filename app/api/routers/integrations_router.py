from fastapi import APIRouter

from app.api.controllers.integrations_controller import router as ep

router = APIRouter(prefix="/integrations", tags=["integrations"])
router.include_router(ep)
