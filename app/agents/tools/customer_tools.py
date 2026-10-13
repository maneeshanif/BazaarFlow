"""The customer-facing agent's write tool (PRD W-003 step 2-3, §36.9): a customer asks for products on WhatsApp.

``request_order`` never records anything. It checks the products and stock with the same preview a person gets, then files
an approval for the shop's owner or manager; the order is posted (and the customer told) only when they approve it. The
customer's phone and name come from the conversation (the run context), never from the model or from the customer's text.
"""

from __future__ import annotations

import uuid
from decimal import Decimal

from agents import function_tool
from pydantic import BaseModel

from app.agent_runtime.context import ProposedAction, RuntimeContext
from app.agents.tools.shop_tools import Ctx, _run, _uuid
from app.core.problems import DomainError
from app.models.agent import ActionStatus, AgentAction
from app.schemas.order import SaleLine, SalePreviewRequest
from app.services import approvals, order_service

MAX_QTY = 500  # a WhatsApp order for more than this is a conversation with a person


class RequestedLine(BaseModel):
    product_id: str
    qty: int


def _rs(value: Decimal) -> str:
    return f"Rs {value:,.0f}"


@function_tool
async def request_order(wrapper: Ctx, items: list[RequestedLine]) -> str:
    """Ask the shop to prepare an order for this customer. Use product ids from find_product and only after the customer
    clearly said what and how many. It does NOT confirm anything: the shop's owner approves it first."""

    async def handler(rc: RuntimeContext, _direct: bool) -> str:
        if not rc.contact_phone:
            raise DomainError("This conversation has no phone number to order for", code="no_contact")
        if not items:
            raise DomainError("Add at least one product", code="no_items")
        lines: list[SaleLine] = []
        for item in items:
            if item.qty < 1 or item.qty > MAX_QTY:
                raise DomainError(f"qty must be between 1 and {MAX_QTY}", code="bad_qty")
            lines.append(SaleLine(product_id=_uuid(item.product_id, "product_id"), qty=item.qty))
        preview = await order_service.preview_sale(
            rc.db, rc.principal, SalePreviewRequest(items=lines, discount=Decimal("0.00"), payment_method="udhaar", amount_paid=None)
        )
        if preview.warnings:
            raise DomainError("; ".join(preview.warnings), code="not_available")
        payload = {
            "items": [{"product_id": str(line.product_id), "qty": line.qty} for line in lines],
            "phone": rc.contact_phone,
            "customer_name": rc.contact_name,
            "conversation_id": str(rc.conversation_id) if rc.conversation_id else None,
        }
        digest = approvals.payload_hash(payload)
        from sqlalchemy import select  # local: the module is imported by the agent runtime at start-up

        waiting = (
            await rc.db.execute(
                select(AgentAction.id).where(
                    AgentAction.tenant_id == rc.principal.tenant_id,
                    AgentAction.status == ActionStatus.pending.value,
                    AgentAction.payload_hash == digest,
                )
            )
        ).first()
        if waiting is not None:
            return "This order request is already with the shop. Tell the customer the shop will confirm it shortly."
        asked: dict[uuid.UUID, int] = {}
        for line in lines:
            asked[line.product_id] = asked.get(line.product_id, 0) + line.qty
        names = ", ".join(f"{asked.get(ln.product_id, 0)} x {ln.product_name}" for ln in preview.lines)
        who = rc.contact_name or rc.contact_phone
        summary = f"Customer order from {who}: {names} = {_rs(preview.total)}"
        action = await approvals.request_action(rc.tool_context(), agent="customer", tool="customer_order", summary=summary, payload=payload)
        rc.actions.append(ProposedAction(id=action.id, tool="customer_order", summary=summary))
        return (
            f"Order request sent to the shop: {names}, total {_rs(preview.total)}. It is NOT confirmed yet: the shop "
            "must approve it first. Tell the customer the shop will confirm shortly. Do not promise a delivery time."
        )

    args = {"items": [i.model_dump() for i in items]}
    return await _run(wrapper, "request_order", args, handler)


CUSTOMER_TOOLS = [request_order]

__all__ = ["CUSTOMER_TOOLS", "RequestedLine", "request_order", "uuid"]
