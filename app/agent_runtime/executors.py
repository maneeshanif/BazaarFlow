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
from app.services import ledger_service, order_service, stock_service


async def post_order_payload(
    db: AsyncSession, principal: Principal, payload: dict[str, Any], *, idempotency_key: str
) -> OrderDetail:
    sale = SaleCreate.model_validate(payload)
    sale = sale.model_copy(update={"stock_override": False})  # an agent can never override the shelf count
    order, _created = await order_service.post_sale(db, principal, sale, idempotency_key=idempotency_key, channel="chat")
    return order


async def execute_action(
    db: AsyncSession, approver: Principal, *, action_id: uuid.UUID, tool: str, requested_by: uuid.UUID | None, payload: dict[str, Any]
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
    raise DomainError(f"Nothing knows how to run the action '{tool}'", code="unknown_action")


__all__ = ["execute_action", "post_order_payload", "TenantRole"]
