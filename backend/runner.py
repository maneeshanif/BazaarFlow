"""Integration glue between webhook events and the Sales Agent runner."""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, Optional

from agents import Runner, SQLiteSession  # type: ignore[import-not-found]

from .my_agents.sales_agent import sales_agent

from .lib import repository

logger = logging.getLogger(__name__)

_SESSIONS: dict[str, SQLiteSession] = {}

_FALLBACK_REPLY = (
    "Thanks for reaching out! A sales specialist will follow up shortly."
)


def _session_key(vendor_id: str, customer_phone: str) -> str:
    return f"{vendor_id}:{customer_phone}"


def _ensure_session(vendor_id: str, customer_phone: str) -> SQLiteSession:
    key = _session_key(vendor_id, customer_phone)
    if key not in _SESSIONS:
        _SESSIONS[key] = SQLiteSession(session_id=key)
    return _SESSIONS[key]


def _build_prompt(
    vendor: Dict[str, Any],
    customer: Dict[str, Any],
    recent: list[Dict[str, Any]],
    incoming_text: str,
) -> str:
    lines: list[str] = []
    lines.append("You are the BazaarFlow WhatsApp sales assistant.")
    lines.append("Use the vendor profile and message history to craft the next reply.")
    lines.append("Respond in <=320 characters. If no confident answer, say you will escalate.")
    lines.append("")
    lines.append("Vendor profile:")
    lines.append(json.dumps({
        "name": vendor.get("name"),
        "settings": vendor.get("settings", {}),
        "waba_id": vendor.get("waba_id"),
    }, ensure_ascii=True))
    lines.append("")
    lines.append("Customer:")
    lines.append(json.dumps({
        "phone": customer.get("phone"),
        "name": customer.get("name"),
    }, ensure_ascii=True))
    if recent:
        lines.append("")
        lines.append("Recent conversation (oldest first):")
        for message in recent:
            role = "customer" if message.get("direction") == "inbound" else "vendor"
            text = message.get("text") or ""
            lines.append(f"- {role}: {text}")
    lines.append("")
    lines.append(f"Incoming message: {incoming_text}")
    lines.append("")
    lines.append("Reply with either plain text or JSON {\"reply_text\": str, \"action\": str, ...}.")
    return "\n".join(lines)


async def runner_hook(
    *,
    vendor: Dict[str, Any],
    customer: Dict[str, Any],
    incoming_message: Dict[str, Any],
    metadata: Dict[str, Any],
) -> Dict[str, Any]:
    """Process incoming message with the sales agent and return reply."""
    
    text = incoming_message.get("text") or ""
    session = _ensure_session(vendor["vendor_id"], customer["phone"])
    recent = repository.recent_messages(vendor["vendor_id"], customer["phone"], limit=10)

    agent_input = _build_prompt(vendor, customer, recent, text)

    try:
        logger.debug("Runner hook invoking agent for vendor %s", vendor["vendor_id"])
        response = await Runner.run(
            starting_agent=sales_agent,
            input=agent_input,
            session=session,
        )
    except Exception:  # pragma: no cover - defensive logging path
        logger.exception("Agent execution failed; returning fallback reply")
        return {"reply_text": _FALLBACK_REPLY, "action": "reply"}

    reply_text: Optional[str] = None
    action = "reply"
    order_payload: Optional[Dict[str, Any]] = None

    final_output = getattr(response, "final_output", None) or str(response)
    if not isinstance(final_output, str):
        final_output = str(final_output)

    trimmed = final_output.strip()
    if not trimmed:
        return {"reply_text": _FALLBACK_REPLY, "action": "reply"}

    # Remove markdown code blocks if present (```json ... ```)
    if trimmed.startswith("```"):
        lines = trimmed.split("\n")
        # Remove first line (```json or ```) and last line (```)
        if len(lines) >= 3:
            trimmed = "\n".join(lines[1:-1]).strip()

    # Try to parse as JSON
    if trimmed.startswith("{"):
        try:
            parsed = json.loads(trimmed)
            if isinstance(parsed, dict):
                reply_candidate = parsed.get("reply_text")
                if isinstance(reply_candidate, str) and reply_candidate.strip():
                    reply_text = reply_candidate.strip()
                action_candidate = parsed.get("action")
                if isinstance(action_candidate, str):
                    action = action_candidate
                payload_candidate = parsed.get("order_payload")
                if isinstance(payload_candidate, dict):
                    order_payload = payload_candidate
        except json.JSONDecodeError:
            logger.debug("Agent returned non-JSON payload despite JSON prefix")

    if reply_text is None:
        reply_text = trimmed

    if not reply_text.strip():
        reply_text = _FALLBACK_REPLY

    result: Dict[str, Any] = {"reply_text": reply_text, "action": action}
    if order_payload:
        result["order_payload"] = order_payload

    return result


__all__ = ["runner_hook"]
