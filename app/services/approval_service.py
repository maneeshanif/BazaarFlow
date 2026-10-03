"""The approvals center (PRD F-021, §36.7): list what agents want to do, then approve, edit or reject it.

Approving runs exactly the stored payload (its hash is re-checked) through ``executors`` in the same transaction, so a
sale approved here is a real sale with stock, payment and udhaar behind it, or it fails and nothing changes. Only owners
and managers decide. Every step is audited (``agent.action_*``).
"""

from __future__ import annotations

import uuid
from typing import Any

from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent_runtime import executors
from app.agents.context import ToolContext
from app.core.audit import record_audit
from app.core.problems import DomainError, NotFound
from app.core.tenancy import Principal
from app.models.agent import ActionStatus, AgentAction
from app.models.user import User
from app.schemas.agent import ApprovalOut
from app.schemas.order import SaleCreate, SalePreviewRequest
from app.services import approvals, order_service


def _ctx(db: AsyncSession, principal: Principal) -> ToolContext:
    return ToolContext(tenant_id=principal.tenant_id, user_id=principal.user_id, role=principal.role, session=db)


def _out(action: AgentAction, requester: str | None) -> ApprovalOut:
    return ApprovalOut(
        id=action.id,
        agent=action.agent,
        tool=action.tool,
        summary=action.summary,
        payload=action.payload_json,
        status=action.status,  # type: ignore[arg-type]
        requested_by=action.requested_by,
        requested_by_name=requester,
        decided_by=action.decided_by,
        decision_note=action.decision_note,
        created_at=action.created_at,
        expires_at=action.expires_at,
        executed_at=action.executed_at,
    )


async def _requester_name(db: AsyncSession, user_id: uuid.UUID | None) -> str | None:
    if user_id is None:
        return None
    row = (await db.execute(select(User.name, User.email).where(User.id == user_id))).first()
    return (row[0] or row[1]) if row else None


async def list_actions(
    db: AsyncSession, principal: Principal, *, status: str | None, limit: int, offset: int
) -> tuple[list[ApprovalOut], int]:
    await approvals.expire_due(_ctx(db, principal))  # a request nobody answered in time is shown as expired
    conditions: list[Any] = [AgentAction.tenant_id == principal.tenant_id]
    if status:
        conditions.append(AgentAction.status == status)
    total = (await db.execute(select(func.count()).select_from(select(AgentAction.id).where(*conditions).subquery()))).scalar_one()
    rows = (
        await db.execute(
            select(AgentAction, User.name, User.email)
            .outerjoin(User, User.id == AgentAction.requested_by)
            .where(*conditions)
            .order_by(AgentAction.created_at.desc(), AgentAction.id.desc())
            .limit(limit)
            .offset(offset)
        )
    ).all()
    return [_out(a, name or email) for a, name, email in rows], int(total)


async def get_action(db: AsyncSession, principal: Principal, action_id: uuid.UUID) -> ApprovalOut:
    row = (
        await db.execute(
            select(AgentAction, User.name, User.email)
            .outerjoin(User, User.id == AgentAction.requested_by)
            .where(AgentAction.id == action_id, AgentAction.tenant_id == principal.tenant_id)
        )
    ).first()
    if row is None:
        raise NotFound("Approval")
    return _out(row[0], row[1] or row[2])


def _translate(exc: Exception) -> DomainError:
    if isinstance(exc, approvals.ActionNotFound):
        return NotFound("Approval")
    if isinstance(exc, PermissionError):
        return DomainError(str(exc), code="forbidden", status_code=403)
    return DomainError(str(exc), code="approval_state", status_code=409)


async def approve(db: AsyncSession, principal: Principal, action_id: uuid.UUID) -> ApprovalOut:
    ctx = _ctx(db, principal)
    try:
        decided = await approvals.decide(ctx, action_id, approve=True)
    except (approvals.ApprovalError, PermissionError) as exc:
        raise _translate(exc) from exc

    async def run(payload: dict[str, Any]) -> None:
        await executors.execute_action(
            db, principal, action_id=decided.id, tool=decided.tool, requested_by=decided.requested_by, payload=payload
        )

    try:
        await approvals.execute(ctx, action_id, run)
    except (approvals.ApprovalError, PermissionError) as exc:
        raise _translate(exc) from exc
    return await get_action(db, principal, action_id)


async def reject(db: AsyncSession, principal: Principal, action_id: uuid.UUID, reason: str) -> ApprovalOut:
    try:
        await approvals.decide(_ctx(db, principal), action_id, approve=False, note=reason)
    except (approvals.ApprovalError, PermissionError) as exc:
        raise _translate(exc) from exc
    return await get_action(db, principal, action_id)


async def _validate(db: AsyncSession, principal: Principal, tool: str, payload: dict[str, Any]) -> None:
    """The edited payload must pass the same checks a fresh request would."""
    if tool == "post_order":
        try:
            sale = SaleCreate.model_validate(payload)
        except ValidationError as exc:
            first = exc.errors()[0]
            raise DomainError(f"{'.'.join(str(p) for p in first['loc'])}: {first['msg']}", code="validation_failed", status_code=422) from exc
        preview = await order_service.preview_sale(
            db,
            principal,
            SalePreviewRequest(items=sale.items, discount=sale.discount, payment_method=sale.payment_method, amount_paid=sale.amount_paid),
        )
        if preview.warnings:
            raise DomainError("; ".join(preview.warnings), code="not_postable")
    elif tool == "record_payment":
        try:
            ok = float(payload["amount"]) > 0 and payload["method"] in ("cash", "card", "bank", "wallet")
        except (KeyError, ValueError, TypeError):
            ok = False
        if not ok:
            raise DomainError("amount must be above zero and method cash, card, bank or wallet", code="validation_failed", status_code=422)
    elif tool == "adjust_stock":
        delta = payload.get("delta")
        if not isinstance(delta, int) or delta == 0 or payload.get("reason") not in ("purchase", "adjustment", "return"):
            raise DomainError("delta must be a whole number other than zero", code="validation_failed", status_code=422)
    else:
        raise DomainError(f"'{tool}' cannot be edited", code="not_editable")


async def edit(db: AsyncSession, principal: Principal, action_id: uuid.UUID, payload: dict[str, Any]) -> ApprovalOut:
    if principal.role.value not in ("owner", "manager"):
        raise DomainError("Only an owner or manager can edit an approval", code="forbidden", status_code=403)
    action = (
        await db.execute(
            select(AgentAction).where(AgentAction.id == action_id, AgentAction.tenant_id == principal.tenant_id).with_for_update()
        )
    ).scalar_one_or_none()
    if action is None:
        raise NotFound("Approval")
    if action.status != ActionStatus.pending.value:
        raise DomainError(f"This approval is {action.status}, so it can no longer be edited", code="approval_state", status_code=409)
    await _validate(db, principal, action.tool, payload)
    before = action.payload_hash
    action.payload_json = payload
    action.payload_hash = approvals.payload_hash(payload)
    await db.flush()
    record_audit(
        db,
        "agent.action_edited",
        tenant_id=principal.tenant_id,
        actor_id=principal.user_id,
        entity="agent_action",
        entity_id=action.id,
        before={"payload_hash": before},
        after={"payload_hash": action.payload_hash},
    )
    return await get_action(db, principal, action_id)

