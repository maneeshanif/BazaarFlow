"""One chat turn with the sales agent, from request to redacted record (build-plan tasks 63, 64, 65).

Before the model is called: the shop's AI switch (the kill switch, flipped by the owner with no deploy) and the monthly
spend cap are checked. During the run: the tool-call cap. After it: tokens and spend are added to the shop's month and a
redacted trace is stored. A provider failure never reaches the user as a stack trace, and anything half-written by a
failed turn is rolled back.
"""

from __future__ import annotations

import time
import uuid
from collections import OrderedDict
from dataclasses import dataclass, field
from datetime import datetime, timezone

from agents import Model, Runner, SQLiteSession
from agents.exceptions import MaxTurnsExceeded
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent_runtime.agents import build_sales_agent
from app.agent_runtime.context import ProposedAction, RuntimeContext
from app.agent_runtime.llm import build_model, describe_failure
from app.agents.tools.shop_tools import forget_drafts
from app.core.settings import settings
from app.core.tenancy import Principal
from app.models.agent_run import AgentRun
from app.models.customer import Customer
from app.models.tenant import Tenant

_MAX_SESSIONS = 300
_SESSIONS: OrderedDict[str, SQLiteSession] = OrderedDict()


def _session(principal: Principal, session_id: str) -> SQLiteSession:
    """Conversation memory, keyed by shop + person + session so nobody can read another's history."""
    key = f"{principal.tenant_id}:{principal.user_id}:{session_id}"
    session = _SESSIONS.get(key)
    if session is None:
        session = SQLiteSession(session_id=key)
        _SESSIONS[key] = session
        while len(_SESSIONS) > _MAX_SESSIONS:
            _SESSIONS.popitem(last=False)
    else:
        _SESSIONS.move_to_end(key)
    return session


def _month_start() -> datetime:
    now = datetime.now(timezone.utc)
    return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


async def month_spend_micros(db: AsyncSession, tenant_id: uuid.UUID) -> int:
    total = (
        await db.execute(
            select(func.coalesce(func.sum(AgentRun.spend_micros), 0)).where(
                AgentRun.tenant_id == tenant_id, AgentRun.created_at >= _month_start()
            )
        )
    ).scalar_one()
    return int(total)


def cap_micros() -> int:
    return int(settings.AGENT_MONTHLY_SPEND_CAP_USD * 1_000_000)


async def shop_switch_on(db: AsyncSession, tenant_id: uuid.UUID) -> bool:
    if not settings.AGENTS_ENABLED:  # the platform-wide switch, set in the environment
        return False
    flag = (await db.execute(select(Tenant.agents_enabled).where(Tenant.id == tenant_id))).scalar_one_or_none()
    return bool(flag)


@dataclass
class AgentReply:
    reply: str
    session_id: str
    outcome: str
    run_id: uuid.UUID
    actions: list[ProposedAction] = field(default_factory=list)
    notice: str | None = None


def _spend(tokens_in: int, tokens_out: int) -> int:
    """USD per million tokens equals micro-dollars per token, so the arithmetic stays in whole numbers."""
    return int(tokens_in * settings.LLM_PRICE_IN_PER_M + tokens_out * settings.LLM_PRICE_OUT_PER_M)


async def _learn_known_people(db: AsyncSession, rc: RuntimeContext) -> None:
    """Teach the redactor every customer of this shop, so a name or number typed by the user is removed from the stored
    trace even when no tool returned it. (A shop's customer list is small; the cap keeps the cost bounded.)"""
    rows = (
        await db.execute(
            select(Customer.name, Customer.phone, Customer.email, Customer.address)
            .where(Customer.tenant_id == rc.principal.tenant_id, Customer.deleted_at.is_(None))
            .limit(5000)
        )
    ).all()
    for name, phone, email, address in rows:
        rc.redactor.learn(name, "customer")
        rc.redactor.learn(phone, "phone")
        rc.redactor.learn(email, "email")
        rc.redactor.learn(address, "address")


async def _record(
    db: AsyncSession,
    rc: RuntimeContext,
    *,
    message: str,
    reply: str,
    outcome: str,
    tokens_in: int = 0,
    tokens_out: int = 0,
    started: float,
    sid: str,
) -> AgentRun:
    await _learn_known_people(db, rc)
    run = AgentRun(
        tenant_id=rc.principal.tenant_id,
        user_id=rc.principal.user_id,
        agent="sales",
        session_id=sid[:80],
        input_text=rc.redactor.text(message),
        output_text=rc.redactor.text(reply),
        trace_json=[
            {"tool": s.tool, "arguments": rc.redactor.data(s.arguments), "result": rc.redactor.text(s.result), "ok": s.ok}
            for s in rc.steps
        ],
        action_ids=[str(a.id) for a in rc.actions],
        outcome=outcome,
        tokens_in=tokens_in,
        tokens_out=tokens_out,
        spend_micros=_spend(tokens_in, tokens_out),
        duration_ms=int((time.monotonic() - started) * 1000),
    )
    db.add(run)
    await db.flush()
    return run


async def run_sales_chat(
    db: AsyncSession, principal: Principal, message: str, session_id: str | None, model: Model | None = None
) -> AgentReply:
    started = time.monotonic()
    sid = session_id or f"chat-{uuid.uuid4().hex[:12]}"
    rc = RuntimeContext(principal=principal, db=db, session_id=f"{principal.tenant_id}:{principal.user_id}:{sid}")

    if not await shop_switch_on(db, principal.tenant_id):
        text = "The AI assistant is paused for this shop. The owner can switch it back on in Agent activity."
        run = await _record(db, rc, message=message, reply=text, outcome="paused", started=started, sid=sid)
        return AgentReply(reply=text, session_id=sid, outcome="paused", run_id=run.id)

    spent = await month_spend_micros(db, principal.tenant_id)
    if spent >= cap_micros():
        text = "This shop has used up its AI allowance for the month, so I cannot help until next month. You can still record sales by hand."
        run = await _record(db, rc, message=message, reply=text, outcome="spend_limit", started=started, sid=sid)
        return AgentReply(reply=text, session_id=sid, outcome="spend_limit", run_id=run.id)

    outcome, tokens_in, tokens_out = "ok", 0, 0
    try:
        async with db.begin_nested():  # a failed turn leaves nothing half done
            agent = build_sales_agent(model or build_model())
            result = await Runner.run(
                agent,
                message,
                context=rc,
                max_turns=settings.AGENT_MAX_TOOL_CALLS + 1,
                session=_session(principal, sid),
            )
            reply = str(result.final_output or "").strip() or "I could not work out a reply. Please say that another way."
            usage = result.context_wrapper.usage
            tokens_in, tokens_out = usage.input_tokens, usage.output_tokens
    except MaxTurnsExceeded:
        outcome = "step_limit"
        reply = "That needed more steps than I am allowed in one go, so I stopped. Nothing was changed. Please break it into smaller requests."
        rc.actions.clear()
    except Exception as error:  # the provider, the network, a bug: always a plain sentence for the user
        outcome = "failed"
        reply = describe_failure(error)
        rc.actions.clear()  # their rows were rolled back with the savepoint
        forget_drafts(rc.session_id)

    run = await _record(db, rc, message=message, reply=reply, outcome=outcome, tokens_in=tokens_in, tokens_out=tokens_out, started=started, sid=sid)
    notice = None
    if outcome == "ok" and (spent + run.spend_micros) * 100 >= cap_micros() * 80:
        notice = "You have used more than 80% of this month's AI allowance."
    return AgentReply(reply=reply, session_id=sid, outcome=outcome, run_id=run.id, actions=list(rc.actions), notice=notice)
