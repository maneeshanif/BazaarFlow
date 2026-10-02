"""Chat endpoints - exact port of backend/controllers/chat_controller.py

Old full paths (prefix /api was added in app.py):
  POST /api/chat/sales
  POST /api/chat/finance
  POST /api/chat/inventory
  GET  /api/health/chat
"""
from __future__ import annotations

import logging
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.core.auth import ALL_ROLES, MANAGER_UP, public_route, require_role
from app.core.tenancy import Principal
from app.services.chat_service import (
    chat_service,
    finance_chat_service,
    inventory_chat_service,
)

logger = logging.getLogger(__name__)
router = APIRouter()


class ChatMessageRequest(BaseModel):
    message: str
    session_id: Optional[str] = None


class ChatMessageResponse(BaseModel):
    response: str
    session_id: str


async def _handle_agent_request(
    handler, request: ChatMessageRequest, principal: Principal, *, log_ctx: str
) -> ChatMessageResponse:
    # The client-visible session id is not a secret, so the stored session is keyed by tenant + id: another tenant
    # sending the same id gets its own empty conversation, never this one's history.
    client_session_id = request.session_id or f"{handler.session_prefix}_{uuid.uuid4().hex[:12]}"
    try:
        response_text, _ = await handler.process_message(
            message=request.message,
            session_id=f"{principal.tenant_id}:{client_session_id}",
        )
        return ChatMessageResponse(response=response_text, session_id=client_session_id)
    except Exception as exc:
        logger.error("Error in %s: %s", log_ctx, exc)
        raise HTTPException(status_code=500, detail="Error processing your request")


@router.post("/chat/sales", response_model=ChatMessageResponse, dependencies=[Depends(require_role(*ALL_ROLES))])
async def chat_with_sales_agent(
    request: ChatMessageRequest, principal: Principal = Depends(require_role(*ALL_ROLES))
):
    """Website chat endpoint for the sales agent."""
    return await _handle_agent_request(chat_service, request, principal, log_ctx="chat_with_sales_agent")


@router.post("/chat/finance", response_model=ChatMessageResponse, dependencies=[Depends(require_role(*MANAGER_UP))])
async def chat_with_finance_agent(
    request: ChatMessageRequest, principal: Principal = Depends(require_role(*MANAGER_UP))
):
    """Chat endpoint for the finance agent."""
    return await _handle_agent_request(finance_chat_service, request, principal, log_ctx="chat_with_finance_agent")


@router.post("/chat/inventory", response_model=ChatMessageResponse, dependencies=[Depends(require_role(*ALL_ROLES))])
async def chat_with_inventory_agent(
    request: ChatMessageRequest, principal: Principal = Depends(require_role(*ALL_ROLES))
):
    """Chat endpoint for the inventory agent."""
    return await _handle_agent_request(inventory_chat_service, request, principal, log_ctx="chat_with_inventory_agent")


@router.get("/health/chat", dependencies=[Depends(public_route)])
async def chat_health():
    return {"status": "chat services are running"}
