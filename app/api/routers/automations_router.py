from fastapi import APIRouter

from app.api.controllers.automations_controller import router as ep

router = APIRouter(prefix="/automations", tags=["automations"])
router.include_router(ep)
