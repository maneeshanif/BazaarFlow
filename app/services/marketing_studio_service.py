"""Marketing studio (PRD F-014): AI drafts a post, a person edits it, sends it for approval. Nothing is published.

A post moves ``draft -> pending_approval -> approved`` (or back to ``draft`` when the approval is rejected, or
``archived`` when removed). Approving only marks it ready: publishing to Facebook arrives with the channel work in
phase 2. Sending for approval uses the same approvals queue as every other agent action.
"""

from __future__ import annotations

import uuid

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent_runtime.marketing_writer import write_draft
from app.agents.context import ToolContext
from app.core.audit import record_audit
from app.core.pagination import Page, next_cursor
from app.core.problems import Conflict, NotFound
from app.core.tenancy import Principal
from app.models.agent import ActionStatus, AgentAction
from app.models.marketing import MarketingPost
from app.models.product import Product
from app.models.tenant import Tenant
from app.schemas.marketing_studio import DraftRequest, PostOut, PostUpdate
from app.services import approvals

DRAFT, PENDING, APPROVED, ARCHIVED = "draft", "pending_approval", "approved", "archived"


async def _open_requests(db: AsyncSession, principal: Principal) -> set[str]:
    """Posts that have an approval still waiting."""
    payloads = (
        (
            await db.execute(
                select(AgentAction.payload_json).where(
                    AgentAction.tenant_id == principal.tenant_id,
                    AgentAction.tool == "approve_post",
                    AgentAction.status == ActionStatus.pending.value,
                    or_(AgentAction.expires_at.is_(None), AgentAction.expires_at > func.now()),
                )
            )
        )
        .scalars()
        .all()
    )
    return {str(p.get("post_id")) for p in payloads}


async def _heal(db: AsyncSession, principal: Principal, posts: list[MarketingPost]) -> None:
    """A post marked pending whose approval was rejected, expired or failed goes back to a draft, so it is never stuck."""
    stuck = [p for p in posts if p.status == PENDING]
    if not stuck:
        return
    open_ids = await _open_requests(db, principal)
    for post in stuck:
        if str(post.id) not in open_ids:
            post.status = DRAFT
    await db.flush()


async def _get(db: AsyncSession, principal: Principal, post_id: uuid.UUID) -> MarketingPost:
    post = (
        await db.execute(
            select(MarketingPost).where(
                MarketingPost.id == post_id, MarketingPost.tenant_id == principal.tenant_id, MarketingPost.status != ARCHIVED
            )
        )
    ).scalar_one_or_none()
    if post is None:
        raise NotFound("That post does not exist")
    await _heal(db, principal, [post])
    return post


def _out(post: MarketingPost) -> PostOut:
    return PostOut.model_validate(
        {**post.__dict__, "title": post.title or "", "message": post.message or "", "hashtags": post.hashtags or ""}
    )


async def create_draft(db: AsyncSession, principal: Principal, brief: DraftRequest) -> PostOut:
    shop = (await db.execute(select(Tenant.name).where(Tenant.id == principal.tenant_id))).scalar_one()
    product_name: str | None = None
    if brief.product_id is not None:
        product_name = (
            await db.execute(
                select(Product.name).where(Product.id == brief.product_id, Product.tenant_id == principal.tenant_id)
            )
        ).scalar_one_or_none()
        if product_name is None:
            raise NotFound("That product does not exist")
    draft = await write_draft(db, principal, shop=shop, brief=brief, product=product_name)
    post = MarketingPost(
        tenant_id=principal.tenant_id, title=draft.title, message=draft.message, hashtags=draft.hashtags, status=DRAFT
    )
    db.add(post)
    await db.flush()
    record_audit(
        db,
        "marketing.draft_created",
        tenant_id=principal.tenant_id,
        actor_id=principal.user_id,
        entity="marketing_post",
        entity_id=post.id,
    )
    return _out(post)


async def list_posts(
    db: AsyncSession, principal: Principal, *, status: str | None, limit: int, offset: int
) -> Page[PostOut]:
    base = select(MarketingPost).where(MarketingPost.tenant_id == principal.tenant_id)
    base = base.where(MarketingPost.status == status) if status else base.where(MarketingPost.status != ARCHIVED)
    total = (await db.execute(select(func.count()).select_from(base.subquery()))).scalar_one()
    rows = (
        (await db.execute(base.order_by(MarketingPost.created_at.desc(), MarketingPost.id).limit(limit).offset(offset)))
        .scalars()
        .all()
    )
    await _heal(db, principal, list(rows))
    return Page[PostOut](
        items=[_out(p) for p in rows], total=int(total), next_cursor=next_cursor(offset, limit, int(total))
    )


async def get_post(db: AsyncSession, principal: Principal, post_id: uuid.UUID) -> PostOut:
    return _out(await _get(db, principal, post_id))


async def update_post(db: AsyncSession, principal: Principal, post_id: uuid.UUID, body: PostUpdate) -> PostOut:
    post = await _get(db, principal, post_id)
    if post.status != DRAFT:
        raise Conflict(
            "Only a draft can be edited. Wait for the decision, or reject it in Approvals to edit it again.",
            code="not_a_draft",
        )
    post.title, post.message, post.hashtags = body.title, body.message, body.hashtags
    await db.flush()
    record_audit(
        db,
        "marketing.draft_edited",
        tenant_id=principal.tenant_id,
        actor_id=principal.user_id,
        entity="marketing_post",
        entity_id=post.id,
    )
    return _out(post)


async def submit_for_approval(db: AsyncSession, principal: Principal, post_id: uuid.UUID) -> PostOut:
    post = await _get(db, principal, post_id)
    if post.status != DRAFT:
        raise Conflict("Only a draft can be sent for approval.", code="not_a_draft")
    await approvals.request_action(
        ToolContext(tenant_id=principal.tenant_id, user_id=principal.user_id, role=principal.role, session=db),
        agent="marketing",
        tool="approve_post",
        summary=f"Approve the post: {post.title}",
        payload={"post_id": str(post.id), "title": post.title, "message": post.message, "hashtags": post.hashtags},
    )
    post.status = PENDING
    await db.flush()
    return _out(post)


async def archive_post(db: AsyncSession, principal: Principal, post_id: uuid.UUID) -> None:
    post = await _get(db, principal, post_id)
    if post.status == PENDING:
        raise Conflict("This post is waiting for approval. Reject it in Approvals first.", code="awaiting_approval")
    post.status = ARCHIVED
    await db.flush()
    record_audit(
        db,
        "marketing.post_archived",
        tenant_id=principal.tenant_id,
        actor_id=principal.user_id,
        entity="marketing_post",
        entity_id=post.id,
    )


async def mark_approved(db: AsyncSession, principal: Principal, post_id: uuid.UUID) -> str:
    """Executor for an approved ``approve_post`` action."""
    post = (
        await db.execute(
            select(MarketingPost).where(MarketingPost.id == post_id, MarketingPost.tenant_id == principal.tenant_id)
        )
    ).scalar_one_or_none()
    if post is None or post.status != PENDING:
        raise Conflict("The post changed after it was sent for approval.", code="post_changed")
    post.status = APPROVED
    await db.flush()
    record_audit(
        db,
        "marketing.post_approved",
        tenant_id=principal.tenant_id,
        actor_id=principal.user_id,
        entity="marketing_post",
        entity_id=post.id,
    )
    return f"Approved the post: {post.title}"
