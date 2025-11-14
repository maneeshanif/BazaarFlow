"""Webhook endpoints for Meta WhatsApp callbacks."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request  # type: ignore[import-not-found]
from fastapi.responses import JSONResponse, PlainTextResponse  # type: ignore[import-not-found]

from ..lib import repository
from ..runner import runner_hook
from ..services.whatsapp import WhatsAppAPIError, send_text_message

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/webhook/test")
async def test_webhook():
    """Simple test endpoint to verify webhook is accessible."""
    logger.info("🧪 Webhook test endpoint accessed")
    return JSONResponse(
        {
            "status": "ok",
            "message": "Webhook endpoint is accessible",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    )


def _meta_verify_token() -> str:
    from os import getenv

    return getenv("META_VERIFY_TOKEN", "test123")


def _iso_timestamp(value: Optional[str]) -> str:
    if not value:
        return datetime.now(timezone.utc).isoformat()
    try:
        if value.isdigit():
            return datetime.fromtimestamp(int(value), tz=timezone.utc).isoformat()
        return datetime.fromisoformat(value).isoformat()
    except Exception:
        return datetime.now(timezone.utc).isoformat()


@router.get("/webhook")
async def verify_webhook(request: Request, verify_token: str = Depends(_meta_verify_token)):
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge", "")

    logger.info("=" * 80)
    logger.info("🔍 WEBHOOK VERIFICATION REQUEST FROM META")
    logger.info("   Mode: %s", mode)
    logger.info("   Token received: %s", token)
    logger.info("   Expected token: %s", verify_token)
    logger.info("   Challenge: %s", challenge)

    if mode == "subscribe" and token == verify_token:
        logger.info("✅ WEBHOOK VERIFICATION SUCCESSFUL!")
        logger.info("=" * 80)
        return PlainTextResponse(challenge)

    logger.error("❌ WEBHOOK VERIFICATION FAILED!")
    logger.error("   Reason: mode=%s, token_match=%s", mode, token == verify_token)
    logger.info("=" * 80)
    raise HTTPException(status_code=403, detail="Invalid verify token")


def _extract_messages(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    messages: List[Dict[str, Any]] = []
    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})
            for message in value.get("messages", []):
                messages.append(
                    {
                        "message": message,
                        "metadata": value.get("metadata", {}),
                        "contacts": value.get("contacts", []),
                    }
                )
    return messages


async def _handle_message(
    *,
    request: Request,
    message: Dict[str, Any],
    metadata: Dict[str, Any],
    contacts: List[Dict[str, Any]],
) -> None:
    logger.info("🔔 Processing webhook message from customer")
    logger.debug("Message payload: %s", message)
    logger.debug("Metadata: %s", metadata)

    phone_number_id = metadata.get("phone_number_id")
    if not phone_number_id:
        logger.warning("Webhook message missing phone_number_id metadata")
        return

    vendor_name = metadata.get("display_phone_number")
    vendor = repository.upsert_vendor(
        phone_number_id=phone_number_id,
        name=vendor_name,
        waba_id=metadata.get("wa_id") or metadata.get("phone_number_id"),
    )
    logger.info("✅ Vendor identified: %s", vendor["vendor_id"])

    customer_phone = message.get("from")
    if not customer_phone:
        logger.warning("Webhook message missing sender phone")
        return

    contact_profile = next((c.get("profile") for c in contacts if c.get("wa_id") == customer_phone), None)
    customer_name = contact_profile.get("name") if isinstance(contact_profile, dict) else None
    customer = repository.upsert_customer(vendor["vendor_id"], phone=customer_phone, name=customer_name)
    logger.info("✅ Customer saved: %s (%s)", customer_phone, customer_name or "No name")

    text = None
    message_type = message.get("type")
    logger.info("📩 Message type: %s", message_type)

    if message_type == "text":
        text = message.get("text", {}).get("body")
        logger.info("💬 Message text: %s", text)
    else:
        logger.warning("⚠️ Non-text message type received: %s", message_type)

    timestamp = _iso_timestamp(message.get("timestamp"))

    repository.record_message(
        vendor_id=vendor["vendor_id"],
        customer_phone=customer_phone,
        direction="inbound",
        text=text,
        raw_payload=message,
        timestamp=timestamp,
    )
    logger.info("✅ Inbound message saved to database")

    logger.info("🤖 Calling AI agent to generate reply...")
    action = await runner_hook(
        vendor=vendor,
        customer=customer,
        incoming_message={"text": text, "raw": message},
        metadata=metadata,
    )
    logger.info("✅ Agent responded: %s", action.get("reply_text", "No reply")[:100])

    reply_text = action.get("reply_text")
    if not reply_text:
        logger.info("⚠️ No reply text produced; skipping outbound send")
        return

    access_token = vendor.get("access_token")
    if not access_token:
        logger.warning("❌ Vendor %s missing access token; cannot reply", vendor["vendor_id"])
        repository.record_message(
            vendor_id=vendor["vendor_id"],
            customer_phone=customer_phone,
            direction="outbound",
            text=reply_text,
            raw_payload={"status": "not_sent", "reason": "missing_access_token"},
            timestamp=_iso_timestamp(None),
        )
        logger.info("✅ Agent reply saved to database (not sent - no token)")
        return

    http_client = request.app.state.http_client
    response = None
    try:
        logger.info("📤 Sending WhatsApp message to %s...", customer_phone)
        response = await send_text_message(
            client=http_client,
            phone_number_id=vendor["phone_number_id"],
            access_token=access_token,
            to=customer_phone,
            body=reply_text,
        )
        logger.info("✅ Successfully sent WhatsApp message to %s", customer_phone)
    except WhatsAppAPIError as exc:
        logger.warning("❌ WhatsApp API rejected message to %s: %s", customer_phone, exc)
        response = {
            "status": "send_failed",
            "source": "whatsapp_api",
            "error": exc.payload,
        }
        if exc.status_code is not None:
            response["http_status"] = exc.status_code
    except Exception as exc:  # pragma: no cover - defensive logging path
        logger.exception("❌ Failed to send outbound WhatsApp message: %s", exc)
        response = {"status": "send_failed", "error": "whatsapp_api_error"}

    repository.record_message(
        vendor_id=vendor["vendor_id"],
        customer_phone=customer_phone,
        direction="outbound",
        text=reply_text,
        raw_payload=response or {"status": "unknown"},
        timestamp=_iso_timestamp(None),
    )
    logger.info("✅ Agent reply saved to database")


@router.post("/webhook")
async def inbound_webhook(request: Request):
    logger.info("=" * 80)
    logger.info("📨 INCOMING WEBHOOK FROM META")
    logger.info("=" * 80)

    try:
        body = await request.json()
        logger.info("📦 Raw webhook payload received")
        logger.info("   Keys: %s", list(body.keys()))
        logger.info("   Object type: %s", body.get("object", "unknown"))

        import json

        logger.debug("Full payload: %s", json.dumps(body, indent=2))
    except Exception as exc:
        logger.error("❌ Failed to parse webhook body: %s", exc)
        return JSONResponse({"status": "error", "message": "Invalid JSON"}, status_code=400)

    messages = _extract_messages(body)
    logger.info("📊 Extracted %d message(s) from webhook", len(messages))

    if not messages:
        logger.warning("⚠️  No messages found in webhook payload")
        logger.info("=" * 80)
        return JSONResponse({"status": "ignored"})

    for index, envelope in enumerate(messages, 1):
        logger.info("📬 Processing message %d/%d", index, len(messages))
        logger.info("   Customer: %s", envelope.get("message", {}).get("from", "unknown"))
        logger.info("   Message ID: %s", envelope.get("message", {}).get("id", "unknown"))

        await _handle_message(
            request=request,
            message=envelope["message"],
            metadata=envelope.get("metadata", {}),
            contacts=envelope.get("contacts", []),
        )

    logger.info("✅ All messages processed successfully")
    logger.info("=" * 80)
    return JSONResponse({"status": "ok"})
