"""VAPI webhook endpoint for BazaarFlow customer support agent.

This controller exposes a single POST endpoint that VAPI can call when
an assistant triggers a function call. It mirrors the behaviour described
in HOW_TO_IMPLEMENT_VAPI.md but implemented in FastAPI/Python.
"""

from __future__ import annotations

from typing import Any, Dict, Optional
import logging
import os

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

from ..services.vapi_support_service import dispatch_tool_call

logger = logging.getLogger(__name__)
router = APIRouter()

VAPI_WEBHOOK_SECRET = os.getenv("VAPI_WEBHOOK_SECRET")


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
    """Handle function-call messages from VAPI.

    This assumes you configure your VAPI assistant with tools whose names match
    those in ``vapi_support_service.TOOL_HANDLERS`` and that the assistant's
    ``serverUrl`` points at this endpoint.
    """

    # Optional: basic shared-secret check. For production, you may want to
    # implement full signature verification per VAPI docs.
    if VAPI_WEBHOOK_SECRET:
        if not x_vapi_signature or x_vapi_signature != VAPI_WEBHOOK_SECRET:
            logger.warning("Rejected VAPI webhook due to missing/invalid signature header")
            raise HTTPException(status_code=401, detail="Invalid VAPI webhook signature")

    message = body.message

    if message.type != "function-call" or not message.functionCall:
        # No-op success for non-function messages so the call can continue.
        logger.info("Received non-function-call VAPI message of type=%s", message.type)
        return {"success": True, "message": None}

    tool_name = message.functionCall.name
    args = message.functionCall.arguments or {}

    logger.info("Handling VAPI function call: %s", tool_name)

    result = dispatch_tool_call(tool_name, args)

    # VAPI expects a top-level ``message`` field that can be spoken.
    return {
        "success": result.get("success", True),
        "result": result,
        "message": result.get("responseMessage"),
    }
