"""Chat endpoints — exact port of backend/controllers/chat_controller.py

Old full paths (prefix /api was added in app.py):
  POST /api/chat/sales
  POST /api/chat/finance
  POST /api/chat/inventory
  GET  /api/health/chat
"""
from __future__ import annotations
from typing import Optional
import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter()


class ChatMessageRequest(BaseModel):
    message: str
    session_id: Optional[str] = None


class ChatMessageResponse(BaseModel):
    response: str
    session_id: str


@router.post("/chat/sales", response_model=ChatMessageResponse)
async def chat_with_sales_agent(request: ChatMessageRequest):
    """Website chat endpoint for the sales agent."""
    # TODO: delegate to app.agents runner with sales_agent
    raise HTTPException(status_code=501, detail="Not yet implemented")


@router.post("/chat/finance", response_model=ChatMessageResponse)
async def chat_with_finance_agent(request: ChatMessageRequest):
    """Chat endpoint for the finance agent."""
    raise HTTPException(status_code=501, detail="Not yet implemented")


@router.post("/chat/inventory", response_model=ChatMessageResponse)
async def chat_with_inventory_agent(request: ChatMessageRequest):
    """Chat endpoint for the inventory agent."""
    raise HTTPException(status_code=501, detail="Not yet implemented")


@router.get("/health/chat")
async def chat_health():
    return {"status": "chat services are running"}
