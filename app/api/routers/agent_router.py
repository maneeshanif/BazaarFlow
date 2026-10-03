from fastapi import APIRouter

from app.api.controllers.agent_controller import approvals_router as approvals_ep
from app.api.controllers.agent_controller import chat_router as chat_ep
from app.api.controllers.agent_controller import runs_router as runs_ep

chat_router = APIRouter(prefix="/chat", tags=["chat"])
chat_router.include_router(chat_ep)

approvals_router = APIRouter(prefix="/approvals", tags=["approvals"])
approvals_router.include_router(approvals_ep)

runs_router = APIRouter(prefix="/agent-runs", tags=["agent-runs"])
runs_router.include_router(runs_ep)
