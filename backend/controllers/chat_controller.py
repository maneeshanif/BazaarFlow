from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import logging
from ..services.chat_service import (
    chat_service,
    finance_chat_service,
    inventory_chat_service,
)

logger = logging.getLogger(__name__)
router = APIRouter()

class ChatMessageRequest(BaseModel):
    message: str
    session_id: Optional[str] = None  # For maintaining conversation context

class ChatMessageResponse(BaseModel):
    response: str
    session_id: str

async def _handle_agent_request(handler, request: ChatMessageRequest, *, log_ctx: str) -> ChatMessageResponse:
    try:
        response_text, session_id = await handler.process_message(
            message=request.message,
            session_id=request.session_id,
        )
        return ChatMessageResponse(response=response_text, session_id=session_id)
    except Exception as exc:  # pragma: no cover - defensive path
        logger.error("Error in %s: %s", log_ctx, exc)
        raise HTTPException(status_code=500, detail="Error processing your request")


@router.post("/chat/sales", response_model=ChatMessageResponse)
async def chat_with_sales_agent(request: ChatMessageRequest):
    """Website chat endpoint for the sales agent."""
    return await _handle_agent_request(chat_service, request, log_ctx="chat_with_sales_agent")


@router.post("/chat/finance", response_model=ChatMessageResponse)
async def chat_with_finance_agent(request: ChatMessageRequest):
    """Chat endpoint for the finance agent."""
    return await _handle_agent_request(finance_chat_service, request, log_ctx="chat_with_finance_agent")


@router.post("/chat/inventory", response_model=ChatMessageResponse)
async def chat_with_inventory_agent(request: ChatMessageRequest):
    """Chat endpoint for the inventory agent."""
    return await _handle_agent_request(inventory_chat_service, request, log_ctx="chat_with_inventory_agent")

@router.get("/health/chat")
async def chat_health():
    """Health check for the chat endpoints."""
    return {"status": "chat services are running"}