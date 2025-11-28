"""VAPI webhook handlers for the BazaarFlow customer support voice agent.

This module defines tool handlers that VAPI can call via function calls.
Each handler takes the tool parameters and returns a dict with a
human-friendly ``responseMessage`` field that the assistant can speak,
as well as any structured data you'd like to log or inspect.
"""

from __future__ import annotations

from typing import Any, Dict, Optional
import logging

from ..lib.json_store import JsonStore

logger = logging.getLogger(__name__)

# Simple JSON-backed ticket store. This keeps the implementation lightweight
# while giving us a durable record of support tickets created by the agent.
_support_ticket_store = JsonStore(
    path="backend/db/support_tickets.json",
    default_factory=lambda: {"tickets": []},
)


def _next_ticket_id(payload: Dict[str, Any]) -> int:
    tickets = payload.get("tickets") or []
    if not isinstance(tickets, list):
        return 1
    return (max((int(t.get("id", 0)) for t in tickets), default=0) + 1)


def handle_create_support_ticket(params: Dict[str, Any]) -> Dict[str, Any]:
    """Create a basic support ticket from VAPI.

    Expected ``params`` schema (define this in VAPI tools):

    - contact: str
    - issue_summary: str
    - details: Optional[str]
    - preferred_channel: Optional[str] ("whatsapp" | "email" | "phone")
    """

    contact = (params.get("contact") or "").strip()
    issue_summary = (params.get("issue_summary") or "").strip()
    details = (params.get("details") or "").strip()
    preferred_channel = (params.get("preferred_channel") or "").strip() or "whatsapp"

    if not contact or not issue_summary:
        msg = (
            "I need at least a contact detail and a short summary of the issue "
            "to create a support ticket. Could you repeat that?"
        )
        return {"success": False, "responseMessage": msg}

    def mutator(current: Dict[str, Any]):
        tickets = current.get("tickets") or []
        if not isinstance(tickets, list):
            tickets = []

        ticket_id = _next_ticket_id(current)
        ticket = {
            "id": ticket_id,
            "contact": contact,
            "issue_summary": issue_summary,
            "details": details,
            "preferred_channel": preferred_channel,
        }
        tickets.append(ticket)
        current["tickets"] = tickets
        return current, ticket

    ticket = _support_ticket_store.update(mutator)

    response_message = (
        f"Thanks. I've created a support ticket number {ticket['id']} "
        f"with the summary: {issue_summary}. Our team will reach out on {preferred_channel}."
    )

    return {
        "success": True,
        "ticket": ticket,
        "responseMessage": response_message,
    }


def handle_check_order_status(params: Dict[str, Any]) -> Dict[str, Any]:
    """Placeholder: look up an order and describe its status.

    For now we don't hit the full sales service to avoid coupling; this can be
    extended later to integrate with sales_service or the JSON DB of orders.
    """

    order_id = (params.get("order_id") or "").strip()
    if not order_id:
        return {
            "success": False,
            "responseMessage": "Please provide an order ID so I can look it up.",
        }

    # TODO: integrate with sales_service or a repository to get real status.
    logger.info("VAPI check_order_status called for order_id=%s", order_id)

    response_message = (
        "I've received your order ID but live order lookups are not yet "
        "wired up in this demo environment. A human support agent will "
        "follow up with you about this order."
    )

    return {"success": True, "order_id": order_id, "responseMessage": response_message}


def handle_check_inventory_item(params: Dict[str, Any]) -> Dict[str, Any]:
    """Placeholder: look up inventory by SKU or name.

    You can later connect this to inventory_service and inventory_items.json.
    """

    sku_or_name = (params.get("sku_or_name") or "").strip()
    if not sku_or_name:
        return {
            "success": False,
            "responseMessage": "Please share the product name or SKU so I can check inventory.",
        }

    logger.info("VAPI check_inventory_item called for query=%s", sku_or_name)

    response_message = (
        "I've noted the item you asked about. In this sandbox, I can't access "
        "live inventory, but a support agent will verify stock levels and get back to you."
    )

    return {
        "success": True,
        "query": sku_or_name,
        "responseMessage": response_message,
    }


def handle_get_marketing_campaign_status(params: Dict[str, Any]) -> Dict[str, Any]:
    """Placeholder: summarize marketing campaign status.

    In a later iteration, wire this into marketing_service and
    marketing_scheduled_repository to report scheduled vs. posted posts.
    """

    campaign_id = (params.get("campaign_id") or "").strip()
    scheduled_only = bool(params.get("scheduled_only"))

    logger.info(
        "VAPI get_marketing_campaign_status called for campaign_id=%s scheduled_only=%s",
        campaign_id or "<any>",
        scheduled_only,
    )

    if campaign_id:
        response_message = (
            "I've logged your question about this marketing campaign. In this demo, "
            "I can't yet fetch the exact status, but our team will review the campaign "
            "and confirm whether it was posted or is still scheduled."
        )
    else:
        response_message = (
            "Right now I can't list all marketing campaigns from this environment, "
            "but a human agent will review your account and share an update shortly."
        )

    return {
        "success": True,
        "campaign_id": campaign_id or None,
        "scheduled_only": scheduled_only,
        "responseMessage": response_message,
    }


# Dispatcher mapping from VAPI functionCall.name -> handler.
TOOL_HANDLERS = {
    "create_support_ticket": handle_create_support_ticket,
    "check_order_status": handle_check_order_status,
    "check_inventory_item": handle_check_inventory_item,
    "get_marketing_campaign_status": handle_get_marketing_campaign_status,
}


def dispatch_tool_call(name: str, params: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Entry point used by the FastAPI controller.

    If an unknown tool is requested, return a graceful message instead of
    raising so the assistant can apologise to the user.
    """

    handler = TOOL_HANDLERS.get(name)
    if handler is None:
        logger.warning("VAPI webhook received unknown tool name: %s", name)
        return {
            "success": False,
            "responseMessage": (
                "I'm not configured to handle that kind of request yet. "
                "A human support agent will follow up if needed."
            ),
        }

    try:
        result = handler(params or {})
    except Exception as exc:  # pragma: no cover - defensive path
        logger.exception("Error while handling VAPI tool %s: %s", name, exc)
        return {
            "success": False,
            "responseMessage": (
                "I ran into an error while handling your request. "
                "Please try again in a moment or contact support via chat."
            ),
        }

    if "responseMessage" not in result:
        # Ensure the assistant always has something to say.
        result["responseMessage"] = "I've completed the requested action."

    return result
