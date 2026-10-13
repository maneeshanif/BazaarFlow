"""What an approved agent action actually does (PRD §36.7: approving runs exactly the stored payload).

Each executor re-validates the payload through the same services a person would use, so an approval can never do
something the rules refuse. The sale is posted as the person who asked (they stay the author on the order), on the
chat channel, with a key derived from the action so a retried approval cannot post it twice.
"""

from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.problems import DomainError
from app.core.tenancy import Principal
from app.models.tenant import TenantRole
from app.schemas.order import OrderDetail, SaleCreate
from app.services import ledger_service, order_service, purchase_order_service, stock_service


async def post_order_payload(
    db: AsyncSession, principal: Principal, payload: dict[str, Any], *, idempotency_key: str
) -> OrderDetail:
    sale = SaleCreate.model_validate(payload)
    sale = sale.model_copy(update={"stock_override": False})  # an agent can never override the shelf count
    order, _created = await order_service.post_sale(
        db, principal, sale, idempotency_key=idempotency_key, channel="chat"
    )
    return order


async def _post_customer_order(db: AsyncSession, approver: Principal, action_id: uuid.UUID, payload: dict[str, Any]) -> str:
    """A customer's WhatsApp order was approved: find or add the customer, post the sale on credit, then confirm to them.

    The sale is on credit (udhaar) because nothing is paid yet; the shop records the payment when it is collected. Stock
    is checked again here, so an order for goods that sold out meanwhile fails with an explanation instead of posting.
    """
    from app.schemas.customer import CustomerCreate  # local imports: avoid a cycle with the services
    from app.services import customer_service
    from app.services.automation_recipes import RecipeError, send_whatsapp

    phone = str(payload["phone"])
    name = payload.get("customer_name") or None
    customer = await customer_service.find_by_phone(db, approver.tenant_id, phone)
    if customer is None:
        created = await customer_service.create_customer(
            db, approver, CustomerCreate(phone=phone if phone.startswith("+") else f"+{phone}", name=str(name) if name else None)
        )
        customer_id, customer_name = created.id, created.name
    else:
        customer_id, customer_name = customer.id, customer.name
    sale = SaleCreate.model_validate(
        {"items": payload["items"], "customer_id": str(customer_id), "payment_method": "udhaar", "stock_override": False}
    )
    order, _created = await order_service.post_sale(db, approver, sale, idempotency_key=f"action-{action_id}", channel="whatsapp")
    greeting = f" {customer_name}" if customer_name else ""
    text = f"Thank you{greeting}! Your order of Rs {order.total:,.0f} is confirmed."
    # the same key as the new-order recipe, so a shop that has that recipe on never confirms the same order twice
    try:
        await send_whatsapp(db, approver.tenant_id, phone, text, f"auto-order-{order.id}")
    except RecipeError:
        return f"Posted order {str(order.id)[:8].upper()} for {order.total}; the WhatsApp confirmation could not be sent"
    return f"Posted order {str(order.id)[:8].upper()} for {order.total} and told the customer"


async def execute_action(
    db: AsyncSession,
    approver: Principal,
    *,
    action_id: uuid.UUID,
    tool: str,
    requested_by: uuid.UUID | None,
    payload: dict[str, Any],
) -> str:
    """Run one approved action; returns a one-line outcome. Raises DomainError when the rules now refuse it."""
    author = Principal(user_id=requested_by or approver.user_id, tenant_id=approver.tenant_id, role=approver.role)
    if tool == "post_order":
        order = await post_order_payload(db, author, payload, idempotency_key=f"action-{action_id}")
        return f"Posted order {str(order.id)[:8].upper()} for {order.total}"
    if tool == "record_payment":
        payment, balance = await ledger_service.record_customer_payment(
            db,
            tenant_id=approver.tenant_id,
            customer_id=uuid.UUID(str(payload["customer_id"])),
            amount=Decimal(str(payload["amount"])),
            method=str(payload["method"]),
            user_id=author.user_id,
        )
        return f"Recorded payment {payment.amount}, balance now {balance}"
    if tool == "adjust_stock":
        movement = await stock_service.record_movement(
            db,
            tenant_id=approver.tenant_id,
            product_id=uuid.UUID(str(payload["product_id"])),
            delta=int(payload["delta"]),
            reason=str(payload["reason"]),
            actor_id=author.user_id,
            actor_type="agent",
            ref_type="agent_action",
            ref_id=action_id,
            note=payload.get("note"),
        )
        return f"Stock changed by {movement.delta}"
    if tool == "approve_post":
        from app.services import marketing_studio_service  # local import: the writer pulls in the whole agent runtime

        return await marketing_studio_service.mark_approved(db, approver, uuid.UUID(str(payload["post_id"])))
    if tool == "approve_comment_reply":
        from app.services import comment_reply_service  # local import: the service pulls in the writer and the adapters

        return await comment_reply_service.mark_approved(db, approver, uuid.UUID(str(payload["comment_reply_id"])))
    if tool == "customer_order":
        return await _post_customer_order(db, approver, action_id, payload)
    if tool == "send_whatsapp_message":
        from app.services.automation_recipes import (  # local import: avoids a cycle with the services
            RecipeError,
            send_whatsapp,
        )

        try:
            sent = await send_whatsapp(db, approver.tenant_id, str(payload["phone"]), str(payload["text"]), f"action-{action_id}")
        except RecipeError as exc:
            raise DomainError(str(exc), code="send_failed") from exc
        # a reorder message that went out completes its draft purchase order (W-006: approved -> sent)
        await purchase_order_service.mark_sent_for_action(db, approver.tenant_id, action_id)
        return "Sent the WhatsApp message" if sent else "That message had already been sent"
    raise DomainError(f"Nothing knows how to run the action '{tool}'", code="unknown_action")


__all__ = ["execute_action", "post_order_payload", "TenantRole"]
