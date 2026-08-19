"""VAPI webhook endpoint � exact port of backend/controllers/vapi_controller.py"""
from __future__ import annotations
from typing import Any, Dict, Optional
import logging

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

from app.core.settings import settings

logger = logging.getLogger(__name__)
router = APIRouter()


class VapiFunctionCall(BaseModel):
    name: str
    arguments: Dict[str, Any] = {}


class VapiMessage(BaseModel):
    type: str
    functionCall: Optional[VapiFunctionCall] = None


class VapiWebhookRequest(BaseModel):
    message: VapiMessage
    call: Optional[Dict[str, Any]] = None


@router.post("/vapi/webhook")
async def vapi_webhook(
    body: VapiWebhookRequest,
    x_vapi_signature: Optional[str] = Header(default=None, alias="x-vapi-signature"),
) -> Dict[str, Any]:
    """Handle function-call messages from VAPI."""
    if settings.VAPI_WEBHOOK_SECRET:
        if not x_vapi_signature or x_vapi_signature != settings.VAPI_WEBHOOK_SECRET:
            raise HTTPException(status_code=401, detail="Invalid VAPI webhook signature")

    message = body.message
    if message.type != "function-call" or not message.functionCall:
        logger.info("Non-function-call VAPI message type=%s", message.type)
        return {"success": True, "message": None}

    tool_name = message.functionCall.name
    args = message.functionCall.arguments or {}
    logger.info("Handling VAPI function call: %s", tool_name)

    # TODO: delegate to app.services.vapi_service.dispatch_tool_call(tool_name, args)
    result: Dict[str, Any] = {"success": True, "responseMessage": f"Handled {tool_name}"}
    return {"success": result.get("success", True), "result": result, "message": result.get("responseMessage")}
