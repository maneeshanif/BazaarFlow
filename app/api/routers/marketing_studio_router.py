from fastapi import APIRouter

from app.api.controllers.marketing_studio_controller import router as ep

router = APIRouter(prefix="/marketing/posts", tags=["marketing"])
router.include_router(ep)
