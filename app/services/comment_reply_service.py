"""Facebook comment replies (PRD W-004 step 4): read the comments on the shop's published posts, propose a reply to each,
and post the approved ones.

Run for one shop by the marketing scheduler's tick, inside that shop's own ``tenant_session``:

1. **Pull and propose.** Posts published in the last 7 days are looked at at most every 10 minutes. Each comment not seen
   before is stored once (the Facebook comment id is unique per shop) and the marketing writer proposes a reply, or
   decides there is nothing worth answering. The shop's ``approval_mode`` decides what happens next: ``auto`` queues the
   reply for posting, ``manual`` files an ``approve_comment_reply`` approval.
2. **Post.** Approved replies are posted through the Facebook adapter with the row id as the idempotency key. A failure that
   can pass is tried again on the next pass, three times in all; a refused token pauses the shop and nothing else is called.

The comment text is public input and untrusted: it is only ever data for the writer, never an instruction, and it never
reaches a tool. When the AI is switched off or its allowance is used up the comment is left unseen and tried again later.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent_runtime.marketing_writer import write_comment_reply
from app.agents.context import ToolContext
from app.core.audit import record_audit
from app.core.problems import Conflict, DomainError, NotFound
from app.core.tenancy import Principal
from app.integrations.http import ProviderError
from app.models.agent import ActionStatus, AgentAction
from app.models.comment_reply import CommentReply
from app.models.marketing import MarketingPost
from app.models.marketing_schedule import MarketingSchedule
from app.models.tenant import Tenant, TenantRole
from app.schemas.comment_replies import CommentReplyOut
from app.services import approvals, integration_service

logger = logging.getLogger("bazaarflow.comments")

COMMENT_ACTOR = uuid.UUID("00000000-0000-0000-0000-00000000a4a4")
WINDOW = timedelta(days=7)  # comments on posts older than this are not looked at
CHECK_EVERY = timedelta(minutes=10)  # how often one post's comments are fetched
MAX_POSTS = 10
MAX_NEW = 10  # new comments answered per pass per shop
MAX_ATTEMPTS = 3
BATCH = 10
MAX_COMMENT_CHARS = 500


@dataclass
class ReplyResult:
    proposed: int = 0
    queued: int = 0
    skipped: int = 0
    posted: int = 0
    failed: int = 0
    paused: int = 0


async def _approval_mode(db: AsyncSession, tenant_id: uuid.UUID) -> str:
    mode = (await db.execute(select(MarketingSchedule.approval_mode).where(MarketingSchedule.tenant_id == tenant_id))).scalar_one_or_none()
    return mode or "manual"  # a shop that never set a schedule confirms every reply


async def pull_and_propose(db: AsyncSession, tenant_id: uuid.UUID, now: datetime) -> ReplyResult:
    result = ReplyResult()
    posts = (
        await db.execute(
            select(MarketingPost)
            .where(
                MarketingPost.tenant_id == tenant_id,
                MarketingPost.status == "published",
                MarketingPost.fb_post_id.is_not(None),
                MarketingPost.published_at >= now - WINDOW,
                or_(MarketingPost.comments_checked_at.is_(None), MarketingPost.comments_checked_at <= now - CHECK_EVERY),
            )
            .order_by(MarketingPost.comments_checked_at.asc().nullsfirst(), MarketingPost.id)
            .limit(MAX_POSTS)
        )
    ).scalars().all()
    if not posts:
        return result
    try:
        adapter = await integration_service.adapter_for(db, tenant_id, "facebook")
    except DomainError:
        result.paused = len(posts)  # not connected, or the token was refused: nothing is called
        return result
    mode = await _approval_mode(db, tenant_id)
    shop = (await db.execute(select(Tenant.name).where(Tenant.id == tenant_id))).scalar_one()
    principal = Principal(user_id=COMMENT_ACTOR, tenant_id=tenant_id, role=TenantRole.manager)
    handled = 0
    try:
        try:
            page_name = await adapter.page_name()
        except ProviderError:
            page_name = None
        for post in posts:
            assert post.fb_post_id is not None
            try:
                comments = await adapter.fetch_comments(post.fb_post_id)
            except ProviderError as error:
                await integration_service.record_failure(db, tenant_id, "facebook", error)
                if error.needs_reconnect:
                    result.paused += 1
                    break  # the rest would be refused too
                continue
            # the unique key is per shop, so "already seen" is checked per shop too
            known = set(
                (
                    await db.execute(
                        select(CommentReply.fb_comment_id).where(
                            CommentReply.tenant_id == tenant_id, CommentReply.fb_comment_id.in_([c.id for c in comments])
                        )
                    )
                ).scalars()
            )
            stopped = False
            for comment in comments:
                if comment.id in known or (page_name and comment.author == page_name):
                    continue  # already handled, or the page's own comment
                if handled >= MAX_NEW:
                    stopped = True
                    break
                text = (comment.message or "").strip()[:MAX_COMMENT_CHARS]
                if not text:
                    continue
                try:
                    async with db.begin_nested():
                        reply = await _propose_one(db, tenant_id, principal, post, comment.id, comment.author, text, shop, mode, result)
                except IntegrityError:  # another pass stored this comment first: nothing to do
                    known.add(comment.id)
                    continue
                except DomainError as error:  # the AI is off, over its allowance, or could not answer: look again later
                    logger.info("comment reply skipped", extra={"tenant_id": str(tenant_id), "reason": error.code})
                    stopped = True
                    break
                handled += 1
                known.add(reply.fb_comment_id)
            if not stopped:
                post.comments_checked_at = now  # only a fully read post waits the interval out
            if stopped:
                break
    finally:
        await adapter.aclose()
    await db.flush()
    return result


async def _propose_one(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    principal: Principal,
    post: MarketingPost,
    comment_id: str,
    author: str | None,
    text: str,
    shop: str,
    mode: str,
    result: ReplyResult,
) -> CommentReply:
    draft = await write_comment_reply(db, principal, shop=shop, post_message=post.message or "", comment=text)
    row = CommentReply(
        tenant_id=tenant_id,
        post_id=post.id,
        fb_post_id=post.fb_post_id or "",
        fb_comment_id=comment_id,
        author=(author or None) and author[:120],
        comment_text=text,
        reply_text=draft.reply,
        status="skipped" if draft.reply is None else ("approved" if mode == "auto" else "proposed"),
    )
    db.add(row)
    await db.flush()
    if draft.reply is None:
        result.skipped += 1
    elif mode == "auto":
        result.queued += 1
    else:
        action = await approvals.request_action(
            ToolContext(tenant_id=tenant_id, user_id=COMMENT_ACTOR, role=TenantRole.manager, session=db),
            agent="marketing",
            tool="approve_comment_reply",
            summary=f"Reply to a comment on your post: {text[:60]}",
            payload={"comment_reply_id": str(row.id), "comment": text, "reply": draft.reply, "author": author},
        )
        row.action_id = action.id
        result.proposed += 1
    record_audit(
        db,
        "marketing.comment_reply_proposed",
        tenant_id=tenant_id,
        actor_type="agent",
        actor_id=COMMENT_ACTOR,
        entity="comment_reply",
        entity_id=row.id,
        after={"status": row.status, "post_id": str(post.id)},
    )
    return row


async def post_approved(db: AsyncSession, tenant_id: uuid.UUID, now: datetime) -> ReplyResult:
    result = ReplyResult()
    due = (
        await db.execute(
            select(CommentReply)
            .where(CommentReply.tenant_id == tenant_id, CommentReply.status == "approved")
            .order_by(CommentReply.created_at, CommentReply.id)
            .limit(BATCH)
            .with_for_update(skip_locked=True)
        )
    ).scalars().all()
    if not due:
        return result
    try:
        adapter = await integration_service.adapter_for(db, tenant_id, "facebook")
    except DomainError:
        result.paused = len(due)
        return result
    try:
        for row in due:
            if row.fb_reply_id:  # already on Facebook (a restart between the call and the commit): never reply twice
                row.status, row.posted_at = "posted", row.posted_at or now
                continue
            try:
                sent = await adapter.reply_to_comment(row.fb_comment_id, row.reply_text or "", idempotency_key=f"reply-{row.id}")
            except ProviderError as error:
                row.attempts += 1
                await integration_service.record_failure(db, tenant_id, "facebook", error)
                if error.needs_reconnect:
                    row.last_error = "Facebook rejected the saved token. Reconnect Facebook."
                    result.paused += 1
                    break
                row.last_error = "Facebook is not answering right now."
                if row.attempts >= MAX_ATTEMPTS:
                    row.status = "failed"
                    result.failed += 1
                continue
            row.fb_reply_id = sent.provider_message_id
            row.status, row.posted_at, row.last_error = "posted", now, None
            row.attempts += 1
            result.posted += 1
            record_audit(
                db,
                "marketing.comment_reply_posted",
                tenant_id=tenant_id,
                actor_type="system",
                entity="comment_reply",
                entity_id=row.id,
                after={"fb_reply_id": row.fb_reply_id},
            )
            await integration_service.record_success(db, tenant_id, "facebook")
    finally:
        await adapter.aclose()
    await db.flush()
    return result


async def run_for_tenant(db: AsyncSession, tenant_id: uuid.UUID, now: datetime) -> ReplyResult:
    """Everything the shop's comments need on one scheduler pass."""
    found = await pull_and_propose(db, tenant_id, now)
    sent = await post_approved(db, tenant_id, now)
    return ReplyResult(
        proposed=found.proposed,
        queued=found.queued,
        skipped=found.skipped,
        posted=sent.posted,
        failed=sent.failed,
        paused=found.paused + sent.paused,
    )


# -- the person's side -------------------------------------------------------------------------------------------


async def mark_approved(db: AsyncSession, principal: Principal, reply_id: uuid.UUID) -> str:
    """Executor for an approved ``approve_comment_reply`` action: the scheduler posts it on its next pass."""
    row = (
        await db.execute(select(CommentReply).where(CommentReply.id == reply_id, CommentReply.tenant_id == principal.tenant_id).with_for_update())
    ).scalar_one_or_none()
    if row is None or row.status != "proposed":
        raise Conflict("The reply changed after it was sent for approval.", code="reply_changed")
    row.status = "approved"
    await db.flush()
    record_audit(
        db,
        "marketing.comment_reply_approved",
        tenant_id=principal.tenant_id,
        actor_id=principal.user_id,
        entity="comment_reply",
        entity_id=row.id,
    )
    return "Approved the reply; it will be posted shortly"


def _out(row: CommentReply, post_title: str | None) -> CommentReplyOut:
    return CommentReplyOut(
        id=row.id,
        post_id=row.post_id,
        post_title=post_title,
        author=row.author,
        comment_text=row.comment_text,
        reply_text=row.reply_text,
        status=row.status,  # type: ignore[arg-type]
        action_id=row.action_id,
        last_error=row.last_error,
        created_at=row.created_at,
        posted_at=row.posted_at,
    )


async def list_replies(
    db: AsyncSession, principal: Principal, *, status: str | None, limit: int, offset: int
) -> tuple[list[CommentReplyOut], int]:
    conditions = [CommentReply.tenant_id == principal.tenant_id]
    if status:
        conditions.append(CommentReply.status == status)
    total = (await db.execute(select(func.count()).select_from(CommentReply).where(*conditions))).scalar_one()
    rows = (
        await db.execute(
            select(CommentReply, MarketingPost.title)
            .join(MarketingPost, MarketingPost.id == CommentReply.post_id)
            .where(*conditions)
            .order_by(CommentReply.created_at.desc(), CommentReply.id.desc())
            .limit(limit)
            .offset(offset)
        )
    ).all()
    return [_out(r, title) for r, title in rows], int(total)


async def skip(db: AsyncSession, principal: Principal, reply_id: uuid.UUID) -> CommentReplyOut:
    """A person decides a proposed (or approved, not yet posted) reply should not go out."""
    found = (
        await db.execute(
            select(CommentReply, MarketingPost.title)
            .join(MarketingPost, MarketingPost.id == CommentReply.post_id)
            .where(CommentReply.id == reply_id, CommentReply.tenant_id == principal.tenant_id)
            .with_for_update(of=CommentReply)
        )
    ).first()
    if found is None:
        raise NotFound("Comment reply")
    row, title = found
    if row.status not in {"proposed", "approved"}:
        raise Conflict("Only a reply that has not been posted can be skipped.", code="not_skippable")
    row.status = "skipped"
    if row.action_id is not None:  # close the approval that was waiting for this reply
        action = (
            await db.execute(select(AgentAction).where(AgentAction.id == row.action_id, AgentAction.tenant_id == principal.tenant_id))
        ).scalar_one_or_none()
        if action is not None and action.status == ActionStatus.pending.value:
            action.status = ActionStatus.rejected.value
            action.decided_by = principal.user_id
            action.decision_note = "The reply was skipped"
    await db.flush()
    record_audit(
        db,
        "marketing.comment_reply_skipped",
        tenant_id=principal.tenant_id,
        actor_id=principal.user_id,
        entity="comment_reply",
        entity_id=row.id,
    )
    return _out(row, title)
