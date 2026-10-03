from fastapi import APIRouter

from app.api.controllers.team_controller import router as ep

router = APIRouter(prefix="/team", tags=["team"])
router.include_router(ep)
