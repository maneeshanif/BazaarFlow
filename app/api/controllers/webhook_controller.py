"""WhatsApp webhook — exact port of backend/controllers/webhook_controller.py"""
from __future__ import annotations
import logging

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.core.settings import settings

logger = logging.getLogger(__name__)
router = APIRouter()


def _extract_messages(body: dict) -> list:
    results = []
    for entry in body.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})
            messages = value.get("messages", [])
            metadata = value.get("metadata", {})
            contacts = value.get("contacts", [])
            for msg in messages:
                results.append({"message": msg, "metadata": metadata, "contacts": contacts})
    return results


@router.get("/webhook/test")
async def webhook_test():
    return {"status": "webhook endpoint is live"}


@router.get("/webhook")
async def verify_webhook(request: Request):
    params = request.query_params
    mode = params.get("hub.mode")
    token = params.get("hub.verify_token")
    challenge = params.get("hub.challenge", "")
    if mode == "subscribe" and token == settings.META_VERIFY_TOKEN:
        logger.info("Webhook verified successfully")
        return JSONResponse(content=int(challenge) if challenge.isdigit() else challenge)
    return JSONResponse({"error": "Forbidden"}, status_code=403)


@router.post("/webhook")
async def inbound_webhook(request: Request):
    logger.info("=" * 60)
    logger.info("INCOMING WEBHOOK FROM META")
    try:
        body = await request.json()
    except Exception as exc:
        logger.error("Failed to parse webhook body: %s", exc)
        return JSONResponse({"status": "error", "message": "Invalid JSON"}, status_code=400)

    messages = _extract_messages(body)
    logger.info("Extracted %d message(s)", len(messages))

    if not messages:
        return JSONResponse({"status": "ignored"})

    for envelope in messages:
        # TODO: delegate to app.services.webhook_service._handle_message(...)
        logger.info("Processing message from: %s", envelope["message"].get("from", "unknown"))

    return JSONResponse({"status": "ok"})
