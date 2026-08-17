from fastapi import APIRouter
from app.api.controllers.chat_controller import router as ep
# No prefix — routes already include /chat/ and /health/ prefixes inside controller
router = APIRouter(prefix="/api", tags=["chat"])
router.include_router(ep)
