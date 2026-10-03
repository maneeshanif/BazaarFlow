"""Agent API (PRD §13.2, F-006, F-021, F-022): the sales chat, the approvals center, the activity log and the AI switch.

Anyone in the shop can chat; owners and managers decide approvals and read the activity log; only the owner flips the
AI switch. Every route is tenant-scoped and audited by the services.
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent_runtime.runtime import run_sales_chat
from app.core.auth import ALL_ROLES, MANAGER_UP, OWNER_ONLY, get_tenant_db, require_role
from app.core.pagination import DEFAULT_LIMIT, MAX_LIMIT, Page, decode_cursor, next_cursor
from app.core.tenancy import Principal
from app.models.agent import AgentAction
from app.schemas.agent import (
    AgentRunDetail,
    AgentRunOut,
    AgentStatus,
    AgentSwitch,
    ApprovalEdit,
    ApprovalOut,
    ApprovalReject,
    ChatAction,
    ChatRequest,
    ChatResponse,
)
from app.services import agent_run_service, approval_service

chat_router = APIRouter()
approvals_router = APIRouter()
runs_router = APIRouter()

TenantDb = Annotated[AsyncSession, Depends(get_tenant_db, scope="function")]
Member = Annotated[Principal, Depends(require_role(*ALL_ROLES))]
Manager = Annotated[Principal, Depends(require_role(*MANAGER_UP))]
Owner = Annotated[Principal, Depends(require_role(*OWNER_ONLY))]


@chat_router.post("/sales", response_model=ChatResponse)
async def chat_with_sales_agent(body: ChatRequest, principal: Member, db: TenantDb) -> ChatResponse:
    """One turn with the sales agent. Anything it wants to change comes back as an approval card, never as a change."""
    reply = await run_sales_chat(db, principal, body.message, body.session_id)
    statuses = {}
    if reply.actions:
        rows = (await db.execute(select(AgentAction.id, AgentAction.status).where(AgentAction.id.in_([a.id for a in reply.actions])))).all()
        statuses = {rid: st for rid, st in rows}
    return ChatResponse(
        reply=reply.reply,
        session_id=reply.session_id,
        outcome=reply.outcome,  # type: ignore[arg-type]
        run_id=reply.run_id,
        actions=[ChatAction(id=a.id, tool=a.tool, summary=a.summary, status=statuses.get(a.id, "pending")) for a in reply.actions],
        notice=reply.notice,
    )


@approvals_router.get("/", response_model=Page[ApprovalOut])
async def list_approvals(
    principal: Manager,
    db: TenantDb,
    status: Annotated[str | None, Query(pattern="^(pending|approved|rejected|executed|failed|expired)$")] = None,
    limit: Annotated[int, Query(ge=1, le=MAX_LIMIT)] = DEFAULT_LIMIT,
    cursor: Annotated[str | None, Query(max_length=60)] = None,
) -> Page[ApprovalOut]:
    offset = decode_cursor(cursor)
    items, total = await approval_service.list_actions(db, principal, status=status, limit=limit, offset=offset)
    return Page[ApprovalOut](items=items, total=total, next_cursor=next_cursor(offset, limit, total))


@approvals_router.get("/{action_id}", response_model=ApprovalOut)
async def get_approval(action_id: UUID, principal: Manager, db: TenantDb) -> ApprovalOut:
    return await approval_service.get_action(db, principal, action_id)


@approvals_router.post("/{action_id}/approve", response_model=ApprovalOut)
async def approve(action_id: UUID, principal: Manager, db: TenantDb) -> ApprovalOut:
    """Approve and run exactly what was proposed. If the rules now refuse it, it is marked failed and nothing changes."""
    return await approval_service.approve(db, principal, action_id)


@approvals_router.post("/{action_id}/reject", response_model=ApprovalOut)
async def reject(action_id: UUID, body: ApprovalReject, principal: Manager, db: TenantDb) -> ApprovalOut:
    return await approval_service.reject(db, principal, action_id, body.reason)


@approvals_router.patch("/{action_id}", response_model=ApprovalOut)
async def edit(action_id: UUID, body: ApprovalEdit, principal: Manager, db: TenantDb) -> ApprovalOut:
    return await approval_service.edit(db, principal, action_id, body.payload)


@runs_router.get("/", response_model=Page[AgentRunOut])
async def list_runs(
    principal: Manager,
    db: TenantDb,
    outcome: Annotated[str | None, Query(pattern="^(ok|failed|step_limit|paused|spend_limit)$")] = None,
    agent: Annotated[str | None, Query(max_length=40)] = None,
    limit: Annotated[int, Query(ge=1, le=MAX_LIMIT)] = DEFAULT_LIMIT,
    cursor: Annotated[str | None, Query(max_length=60)] = None,
) -> Page[AgentRunOut]:
    offset = decode_cursor(cursor)
    items, total = await agent_run_service.list_runs(db, principal, outcome=outcome, agent=agent, limit=limit, offset=offset)
    return Page[AgentRunOut](items=items, total=total, next_cursor=next_cursor(offset, limit, total))


@runs_router.get("/status", response_model=AgentStatus)
async def agent_status(principal: Manager, db: TenantDb) -> AgentStatus:
    return await agent_run_service.status(db, principal)


@runs_router.put("/switch", response_model=AgentStatus)
async def set_agent_switch(body: AgentSwitch, principal: Owner, db: TenantDb) -> AgentStatus:
    """The owner's kill switch: takes effect on the very next message, no deploy."""
    return await agent_run_service.set_switch(db, principal, body.enabled)


@runs_router.get("/{run_id}", response_model=AgentRunDetail)
async def get_run(run_id: UUID, principal: Manager, db: TenantDb) -> AgentRunDetail:
    return await agent_run_service.get_run(db, principal, run_id)
