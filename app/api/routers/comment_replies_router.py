from fastapi import APIRouter

from app.api.controllers.comment_replies_controller import router as ep

router = APIRouter(prefix="/marketing/comments", tags=["marketing"])
router.include_router(ep)
