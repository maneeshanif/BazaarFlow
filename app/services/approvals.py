"""Approval queue for agent actions (PRD §36.7, W-005).

An agent never executes a risky change directly: it files a pending ``agent_actions`` row with the exact
payload. A manager or owner approves it, and execution runs *only* the stored payload (its hash is
re-checked), so what was approved is what runs.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from collections.abc import Awaitable, Callable
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select

from app.agents.context import ToolContext
from app.core.audit import record_audit
from app.models.agent import ActionStatus, AgentAction
from app.models.tenant import TenantRole

DEFAULT_TTL_HOURS = 24


class ApprovalError(Exception):
    """The action cannot move to the requested state."""


class ActionNotFound(ApprovalError):
    """No such action in this shop (an unknown id and another shop's id look the same)."""


def payload_hash(payload: dict[str, Any]) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _now() -> datetime:
    return datetime.now(timezone.utc)


async def _get(ctx: ToolContext, action_id: uuid.UUID, *, lock: bool = False) -> AgentAction:
    stmt = select(AgentAction).where(AgentAction.tenant_id == ctx.tenant_id, AgentAction.id == action_id)
    if lock:
        # FOR UPDATE serialises concurrent decide/execute calls on the same action (no double execution)
        stmt = stmt.with_for_update()
    action = (await ctx.session.execute(stmt)).scalar_one_or_none()
    if action is None:
        raise ActionNotFound("action not found")
    return action


async def request_action(
    ctx: ToolContext,
    *,
    agent: str,
    tool: str,
    summary: str,
    payload: dict[str, Any],
    ttl_hours: int = DEFAULT_TTL_HOURS,
) -> AgentAction:
    action = AgentAction(
        tenant_id=ctx.tenant_id,
        agent=agent,
        tool=tool,
        summary=summary[:500],
        payload_json=payload,
        payload_hash=payload_hash(payload),
        status=ActionStatus.pending.value,
        requested_by=ctx.user_id,
        expires_at=_now() + timedelta(hours=ttl_hours),
    )
    ctx.session.add(action)
    await ctx.session.flush()
    record_audit(
        ctx.session,
        "agent.action_requested",
        tenant_id=ctx.tenant_id,
        actor_type="agent",
        actor_id=agent,
        entity="agent_action",
        entity_id=action.id,
        after={"tool": tool, "summary": action.summary, "payload_hash": action.payload_hash},
    )
    return action


async def decide(ctx: ToolContext, action_id: uuid.UUID, *, approve: bool, note: str | None = None) -> AgentAction:
    if ctx.role not in (TenantRole.owner, TenantRole.manager):
        raise PermissionError("only an owner or manager can decide an approval")
    action = await _get(ctx, action_id, lock=True)
    if action.status != ActionStatus.pending.value:
        raise ApprovalError(f"action is {action.status}, not pending")
    if action.expires_at is not None and action.expires_at <= _now():
        # Refuse without writing: raising rolls the transaction back, so persisting the expiry is the sweep's job.
        raise ApprovalError("action expired")
    action.status = ActionStatus.approved.value if approve else ActionStatus.rejected.value
    action.decided_by = ctx.user_id
    action.decision_note = note
    await ctx.session.flush()
    record_audit(
        ctx.session,
        "agent.action_approved" if approve else "agent.action_rejected",
        tenant_id=ctx.tenant_id,
        actor_id=ctx.user_id,
        entity="agent_action",
        entity_id=action.id,
        after={"note": note},
    )
    return action


async def execute(
    ctx: ToolContext, action_id: uuid.UUID, executor: Callable[[dict[str, Any]], Awaitable[None]]
) -> AgentAction:
    """Run an approved action's stored payload through ``executor``; marks it executed or failed.

    The executor runs inside a savepoint, so if it fails none of its partial writes survive.
    """
    if ctx.role not in (TenantRole.owner, TenantRole.manager):
        raise PermissionError("only an owner or manager can execute an approved action")
    action = await _get(ctx, action_id, lock=True)
    if action.status != ActionStatus.approved.value:
        raise ApprovalError(f"action is {action.status}, not approved")
    if payload_hash(action.payload_json) != action.payload_hash:
        action.status = ActionStatus.failed.value
        await ctx.session.flush()
        raise ApprovalError("payload no longer matches the approved hash")
    try:
        async with ctx.session.begin_nested():
            await executor(action.payload_json)
    except Exception as exc:
        action.status = ActionStatus.failed.value
        # a rule that now refuses the action explains itself; anything else is named by type, never by message
        reason = getattr(exc, "detail", None) if isinstance(getattr(exc, "detail", None), str) else type(exc).__name__
        action.decision_note = f"execution failed: {reason}"[:250]
    else:
        action.status = ActionStatus.executed.value
        action.executed_at = _now()
    await ctx.session.flush()
    record_audit(
        ctx.session,
        "agent.action_executed" if action.status == ActionStatus.executed.value else "agent.action_failed",
        tenant_id=ctx.tenant_id,
        actor_type="system",
        entity="agent_action",
        entity_id=action.id,
        after={"status": action.status, "payload_hash": action.payload_hash},
    )
    return action


async def expire_due(ctx: ToolContext) -> int:
    """Mark pending actions past their expiry as ``expired`` (one audit row each); returns how many."""
    due = (
        (
            await ctx.session.execute(
                select(AgentAction).where(
                    AgentAction.tenant_id == ctx.tenant_id,
                    AgentAction.status == ActionStatus.pending.value,
                    AgentAction.expires_at <= _now(),
                )
            )
        )
        .scalars()
        .all()
    )
    for action in due:
        action.status = ActionStatus.expired.value
        record_audit(
            ctx.session,
            "agent.action_expired",
            tenant_id=ctx.tenant_id,
            actor_type="system",
            entity="agent_action",
            entity_id=action.id,
        )
    await ctx.session.flush()
    return len(due)
