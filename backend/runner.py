"""
Improved WhatsApp-safe Runner Hook.
Solves:
- Status-only webhook payloads
- Duplicate message execution
- Agent delegation consistency
- Better JSON parsing and sanitization
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, Optional

from agents import Runner, SQLiteSession  # type: ignore[import-not-found]

from .my_agents.sales_agent import sales_agent
from .lib import repository

logger = logging.getLogger(__name__)

# ---------------------------------------------------------
# GLOBAL SESSION STORE
# ---------------------------------------------------------

_SESSIONS: dict[str, SQLiteSession] = {}

# Track processed WhatsApp message_ids to prevent duplicates
_PROCESSED_MESSAGE_IDS: set[str] = set()

_FALLBACK_REPLY = (
    "Thanks for reaching out! A sales specialist will follow up shortly."
)


# ---------------------------------------------------------
# SESSION HELPERS
# ---------------------------------------------------------

def _session_key(vendor_id: str, customer_phone: str) -> str:
    return f"{vendor_id}:{customer_phone}"


def _ensure_session(vendor_id: str, customer_phone: str) -> SQLiteSession:
    key = _session_key(vendor_id, customer_phone)
    if key not in _SESSIONS:
        _SESSIONS[key] = SQLiteSession(session_id=key)
    return _SESSIONS[key]


# ---------------------------------------------------------
# PROMPT BUILDER
# ---------------------------------------------------------

def _build_prompt(
    vendor: Dict[str, Any],
    customer: Dict[str, Any],
    recent: list[Dict[str, Any]],
    incoming_text: str,
) -> str:
    """
    Clean and compact prompt for best agent reasoning.
    """
    lines: list[str] = []

    lines.append("You are the BazaarFlow multi-agent Sales Assistant.")
    lines.append("You may call tools like inventory_agent or finance_agent if needed.")
    lines.append("Respond with short, clear text (<=320 chars).")
    lines.append("If sending JSON, only return keys: reply_text, action, order_payload.")
    lines.append("")

    lines.append("Vendor:")
    lines.append(json.dumps({
        "name": vendor.get("name"),
        "settings": vendor.get("settings", {}),
    }, ensure_ascii=True))

    lines.append("\nCustomer:")
    lines.append(json.dumps({
        "phone": customer.get("phone"),
        "name": customer.get("name"),
    }, ensure_ascii=True))

    if recent:
        lines.append("\nConversation history:")
        for m in recent:
            speaker = "customer" if m.get("direction") == "inbound" else "vendor"
            msg = m.get("text") or ""
            lines.append(f"- {speaker}: {msg}")

    lines.append("\nIncoming message:")
    lines.append(incoming_text)

    return "\n".join(lines)


# ---------------------------------------------------------
# MAIN RUNNER
# ---------------------------------------------------------

async def runner_hook(
    *,
    vendor: Dict[str, Any],
    customer: Dict[str, Any],
    incoming_message: Dict[str, Any],
    metadata: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Processes WhatsApp message + runs multi-agent flow safely.
    """

    # -----------------------------------------------------
    # 1. Extract text and WhatsApp message_id
    # -----------------------------------------------------
    text = incoming_message.get("text") or ""
    message_id = incoming_message.get("id")  # Important for dedupe

    # No text = status, reaction, media without text
    if not text.strip():
        logger.info("Skipping agent run: no inbound text found in message.")
        return {"skip": True}

    # -----------------------------------------------------
    # 2. Deduplicate: WhatsApp can resend same message
    # -----------------------------------------------------
    if message_id and message_id in _PROCESSED_MESSAGE_IDS:
        logger.info("Skipping duplicate message %s", message_id)
        return {"skip": True}

    if message_id:
        _PROCESSED_MESSAGE_IDS.add(message_id)

    # -----------------------------------------------------
    # 3. Load session and recent context
    # -----------------------------------------------------
    session = _ensure_session(vendor["vendor_id"], customer["phone"])
    recent = repository.recent_messages(
        vendor["vendor_id"], customer["phone"], limit=12
    )

    agent_input = _build_prompt(vendor, customer, recent, text)

    # -----------------------------------------------------
    # 4. Run the multi-agent system
    # -----------------------------------------------------
    try:
        logger.debug("Running multi-agent pipeline for vendor=%s", vendor["vendor_id"])
        response = await Runner.run(
            starting_agent=sales_agent,
            input=agent_input,
            session=session,
        )
    except Exception as e:
        logger.exception("Agent crash. Returning fallback message.")
        return {"reply_text": _FALLBACK_REPLY, "action": "reply"}

    # -----------------------------------------------------
    # 5. Parse agent output safely
    # -----------------------------------------------------
    final_raw = getattr(response, "final_output", None) or str(response)
    final_raw = final_raw.strip()

    # strip Markdown fences
    if final_raw.startswith("```"):
        parts = final_raw.split("\n")
        if len(parts) >= 3:
            final_raw = "\n".join(parts[1:-1]).strip()

    reply_text = None
    action = "reply"
    order_payload = None

    # JSON MODE:
    if final_raw.startswith("{"):
        try:
            parsed = json.loads(final_raw)
            if isinstance(parsed, dict):
                reply_text = parsed.get("reply_text") or reply_text
                action = parsed.get("action", action)
                order_payload = parsed.get("order_payload")
        except Exception:
            logger.warning("Agent returned invalid JSON. Using raw text.")

    # FALLBACK to plain text
    if not reply_text:
        reply_text = final_raw or _FALLBACK_REPLY

    return_result = {
        "reply_text": reply_text.strip(),
        "action": action,
    }

    if order_payload:
        return_result["order_payload"] = order_payload

    return return_result


__all__ = ["runner_hook"]






# """Integration glue between webhook events and the Sales Agent runner."""

# from __future__ import annotations

# import json
# import logging
# from typing import Any, Dict, Optional

# from agents import Runner, SQLiteSession  # type: ignore[import-not-found]

# from .my_agents.sales_agent import sales_agent

# from .lib import repository

# logger = logging.getLogger(__name__)

# _SESSIONS: dict[str, SQLiteSession] = {}

# _FALLBACK_REPLY = (
#     "Thanks for reaching out! A sales specialist will follow up shortly."
# )


# def _session_key(vendor_id: str, customer_phone: str) -> str:
#     return f"{vendor_id}:{customer_phone}"


# def _ensure_session(vendor_id: str, customer_phone: str) -> SQLiteSession:
#     key = _session_key(vendor_id, customer_phone)
#     if key not in _SESSIONS:
#         _SESSIONS[key] = SQLiteSession(session_id=key)
#     return _SESSIONS[key]


# def _build_prompt(
#     vendor: Dict[str, Any],
#     customer: Dict[str, Any],
#     recent: list[Dict[str, Any]],
#     incoming_text: str,
# ) -> str:
#     lines: list[str] = []
#     lines.append("You are the BazaarFlow WhatsApp sales assistant.")
#     lines.append("Use the vendor profile and message history to craft the next reply.")
#     lines.append("Respond in <=320 characters. If no confident answer, say you will escalate.")
#     lines.append("")
#     lines.append("Vendor profile:")
#     lines.append(json.dumps({
#         "name": vendor.get("name"),
#         "settings": vendor.get("settings", {}),
#         "waba_id": vendor.get("waba_id"),
#     }, ensure_ascii=True))
#     lines.append("")
#     lines.append("Customer:")
#     lines.append(json.dumps({
#         "phone": customer.get("phone"),
#         "name": customer.get("name"),
#     }, ensure_ascii=True))
#     if recent:
#         lines.append("")
#         lines.append("Recent conversation (oldest first):")
#         for message in recent:
#             role = "customer" if message.get("direction") == "inbound" else "vendor"
#             text = message.get("text") or ""
#             lines.append(f"- {role}: {text}")
#     lines.append("")
#     lines.append(f"Incoming message: {incoming_text}")
#     lines.append("")
#     lines.append("Reply with either plain text or JSON {\"reply_text\": str, \"action\": str, ...}.")
#     return "\n".join(lines)


# async def runner_hook(
#     *,
#     vendor: Dict[str, Any],
#     customer: Dict[str, Any],
#     incoming_message: Dict[str, Any],
#     metadata: Dict[str, Any],
# ) -> Dict[str, Any]:
#     """Process incoming message with the sales agent and return reply."""
    
#     text = incoming_message.get("text") or ""
#     session = _ensure_session(vendor["vendor_id"], customer["phone"])
#     recent = repository.recent_messages(vendor["vendor_id"], customer["phone"], limit=10)

#     agent_input = _build_prompt(vendor, customer, recent, text)

#     try:
#         logger.debug("Runner hook invoking agent for vendor %s", vendor["vendor_id"])
#         response = await Runner.run(
#             starting_agent=sales_agent,
#             input=agent_input,
#             session=session,
#         )
#     except Exception:  # pragma: no cover - defensive logging path
#         logger.exception("Agent execution failed; returning fallback reply")
#         return {"reply_text": _FALLBACK_REPLY, "action": "reply"}

#     reply_text: Optional[str] = None
#     action = "reply"
#     order_payload: Optional[Dict[str, Any]] = None

#     final_output = getattr(response, "final_output", None) or str(response)
#     if not isinstance(final_output, str):
#         final_output = str(final_output)

#     trimmed = final_output.strip()
#     if not trimmed:
#         return {"reply_text": _FALLBACK_REPLY, "action": "reply"}

#     # Remove markdown code blocks if present (```json ... ```)
#     if trimmed.startswith("```"):
#         lines = trimmed.split("\n")
#         # Remove first line (```json or ```) and last line (```)
#         if len(lines) >= 3:
#             trimmed = "\n".join(lines[1:-1]).strip()

#     # Try to parse as JSON
#     if trimmed.startswith("{"):
#         try:
#             parsed = json.loads(trimmed)
#             if isinstance(parsed, dict):
#                 reply_candidate = parsed.get("reply_text")
#                 if isinstance(reply_candidate, str) and reply_candidate.strip():
#                     reply_text = reply_candidate.strip()
#                 action_candidate = parsed.get("action")
#                 if isinstance(action_candidate, str):
#                     action = action_candidate
#                 payload_candidate = parsed.get("order_payload")
#                 if isinstance(payload_candidate, dict):
#                     order_payload = payload_candidate
#         except json.JSONDecodeError:
#             logger.debug("Agent returned non-JSON payload despite JSON prefix")

#     if reply_text is None:
#         reply_text = trimmed

#     if not reply_text.strip():
#         reply_text = _FALLBACK_REPLY

#     result: Dict[str, Any] = {"reply_text": reply_text, "action": action}
#     if order_payload:
#         result["order_payload"] = order_payload

#     return result


# __all__ = ["runner_hook"]
