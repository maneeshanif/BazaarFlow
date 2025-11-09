from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import logging
from services.chat_service import chat_service

logger = logging.getLogger(__name__)
router = APIRouter()

class ChatMessageRequest(BaseModel):
    message: str
    session_id: Optional[str] = None  # For maintaining conversation context

class ChatMessageResponse(BaseModel):
    response: str
    session_id: str

@router.post("/chat/sales", response_model=ChatMessageResponse)
async def chat_with_sales_agent(request: ChatMessageRequest):
    """
    Chat endpoint for the sales agent that works through the website
    """
    try:
        # Process the message using the chat service
        response_text, session_id = await chat_service.process_message(
            message=request.message,
            session_id=request.session_id
        )
        
        return ChatMessageResponse(
            response=response_text,
            session_id=session_id
        )
        
    except Exception as e:
        logger.error(f"Error in chat_with_sales_agent: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing your request: {str(e)}")

@router.get("/health/chat")
async def chat_health():
    """Health check for the chat endpoint"""
    return {"status": "chat service is running"}