"""The marketing scheduler (PRD W-004, build-plan tasks 75 and 76): drafts the day's posts and publishes the queued ones.

One ``tick`` (run by ``app.cli.run_scheduler`` every few minutes) does two things for every shop that has work:

1. **Generate.** A shop with its schedule switched on and Facebook connected gets, once per local day and inside its
   posting window, ``posts_per_day`` drafts written by the marketing writer and spread evenly across the window. With
   ``approval_mode = auto`` a draft goes straight to ``queued``; with ``manual`` it files an ``approve_post`` approval and
   is queued when a person approves it. A picture from Pexels is attached when a key is configured (best effort).
2. **Publish.** Every ``queued`` post whose time has come is published to the shop's Facebook Page. A failure that can pass
   (a timeout, a 5xx, throttling) is retried at +5 then +15 minutes and then the post is ``failed`` and stays visible in the
   activity list with its reason and a Retry button. A refused token pauses the shop: its integration goes to ``error``, its
   queued posts wait, and nothing is called until the owner pastes a new token. A post whose ``fb_post_id`` is already set is
   never published twice (the idempotency that survives a restart).

The scan for "which shops have work" is the only cross-shop read (``system_session``, ids only); all work happens inside
each shop's own ``tenant_session``.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent_runtime.marketing_writer import write_draft
from app.agents.context import ToolContext
from app.core.audit import record_audit
from app.core.problems import DomainError
from app.core.tenancy import Principal, system_session, tenant_session
from app.integrations import factory
from app.integrations.http import ProviderError
from app.models.comment_reply import CommentReply
from app.models.marketing import MarketingPost
from app.models.marketing_schedule import MarketingSchedule
from app.models.tenant import Tenant, TenantRole
from app.schemas.marketing_studio import DraftRequest
from app.services import approvals, comment_reply_service, integration_service
from app.services.report_service import SHOP_TZ

logger = logging.getLogger("bazaarflow.scheduler")

MARKETING_ACTOR = uuid.UUID("00000000-0000-0000-0000-00000000a2a2")
MAX_ATTEMPTS = 3
RETRY_DELAYS = (timedelta(minutes=5), timedelta(minutes=15))
BATCH = 10
IMAGE_QUERY = {"announce_offer": "shopping sale", "festival_greeting": "festival celebration", "general": "local shop"}


@dataclass
class TickResult:
    generated: int = 0
    published: int = 0
    retried: int = 0
    failed: int = 0
    paused: int = 0
    replies_proposed: int = 0
    replies_posted: int = 0

    def add(self, other: TickResult) -> None:
        self.generated += other.generated
        self.published += other.published
        self.retried += other.retried
        self.failed += other.failed
        self.paused += other.paused
        self.replies_proposed += other.replies_proposed
        self.replies_posted += other.replies_posted


def slots_for(day: date, start: time, end: time, count: int) -> list[datetime]:
    """``count`` times spread evenly across the window of a local day, as UTC moments (the middle of each equal share)."""
    begin = datetime.combine(day, start, tzinfo=SHOP_TZ)
    span = datetime.combine(day, end, tzinfo=SHOP_TZ) - begin
    return [(begin + span * (2 * i + 1) / (2 * count)).astimezone(timezone.utc) for i in range(count)]


def _text(post: MarketingPost) -> str:
    return "\n\n".join(part for part in (post.message, post.hashtags) if part)


def _principal(tenant_id: uuid.UUID) -> Principal:
    return Principal(user_id=MARKETING_ACTOR, tenant_id=tenant_id, role=TenantRole.manager)


async def _image_for(goal: str) -> str | None:
    """A stock picture for the post, or nothing: a missing key or a provider hiccup never blocks a post."""
    client = factory.build_pexels()
    try:
        images = await client.search(IMAGE_QUERY.get(goal, "local shop"), per_page=3)
    except ProviderError as error:
        logger.warning("image search failed", extra={"provider": "pexels", "kind": error.kind})
        return None
    finally:
        await client.aclose()
    return images[0].url if images else None


async def generate_for_tenant(db: AsyncSession, tenant_id: uuid.UUID, now: datetime) -> int:
    """Draft today's posts when the schedule is on, Facebook works, and the window has opened. Returns how many."""
    schedule = (await db.execute(select(MarketingSchedule).where(MarketingSchedule.tenant_id == tenant_id))).scalar_one_or_none()
    if schedule is None or not schedule.enabled:
        return 0
    local = now.astimezone(SHOP_TZ)
    if schedule.last_generated_on == local.date() or local.time() < schedule.window_start or local.time() >= schedule.window_end:
        return 0
    try:
        await integration_service.adapter_for(db, tenant_id, "facebook")  # nowhere to publish: do not spend the AI allowance
    except DomainError:
        return 0

    shop = (await db.execute(select(Tenant.name).where(Tenant.id == tenant_id))).scalar_one()
    principal = _principal(tenant_id)
    brief = DraftRequest(goal=schedule.goal, tone=schedule.tone, language=schedule.language, notes=schedule.notes)  # type: ignore[arg-type]
    midnight = datetime.combine(local.date(), time.min, tzinfo=SHOP_TZ).astimezone(timezone.utc)
    already = (
        await db.execute(
            select(func.count())
            .select_from(MarketingPost)
            .where(MarketingPost.tenant_id == tenant_id, MarketingPost.source == "schedule", MarketingPost.created_at >= midnight)
        )
    ).scalar_one()  # a half-finished day (the AI ran out of allowance part way) resumes instead of starting over
    created = 0
    for slot in slots_for(local.date(), schedule.window_start, schedule.window_end, schedule.posts_per_day)[int(already) :]:
        try:
            async with db.begin_nested():
                draft = await write_draft(db, principal, shop=shop, brief=brief, product=None)
                post = MarketingPost(
                    tenant_id=tenant_id,
                    title=draft.title,
                    message=draft.message,
                    hashtags=draft.hashtags,
                    image_url=await _image_for(schedule.goal),
                    status="queued" if schedule.approval_mode == "auto" else "pending_approval",
                    scheduled_for=max(slot, now + timedelta(minutes=1)),
                    source="schedule",
                )
                db.add(post)
                await db.flush()
                if schedule.approval_mode == "manual":
                    await approvals.request_action(
                        ToolContext(tenant_id=tenant_id, user_id=MARKETING_ACTOR, role=TenantRole.manager, session=db),
                        agent="marketing",
                        tool="approve_post",
                        summary=f"Approve the scheduled post: {post.title}",
                        payload={"post_id": str(post.id), "title": post.title, "message": post.message, "hashtags": post.hashtags},
                    )
                record_audit(
                    db,
                    "marketing.scheduled_post_created",
                    tenant_id=tenant_id,
                    actor_type="agent",
                    actor_id=MARKETING_ACTOR,
                    entity="marketing_post",
                    entity_id=post.id,
                    after={"status": post.status, "scheduled_for": post.scheduled_for.isoformat() if post.scheduled_for else None},
                )
        except DomainError as error:  # the AI is switched off or the allowance is used up: try again on a later tick
            logger.info("scheduled draft skipped", extra={"tenant_id": str(tenant_id), "reason": error.code})
            return created
        created += 1
    schedule.last_generated_on = local.date()
    await db.flush()
    return created


async def publish_for_tenant(db: AsyncSession, tenant_id: uuid.UUID, now: datetime) -> TickResult:
    """Publish this shop's queued posts that are due."""
    result = TickResult()
    due = (
        await db.execute(
            select(MarketingPost)
            .where(MarketingPost.tenant_id == tenant_id, MarketingPost.status == "queued", MarketingPost.scheduled_for <= now)
            .order_by(MarketingPost.scheduled_for, MarketingPost.id)
            .limit(BATCH)
            .with_for_update(skip_locked=True)
        )
    ).scalars().all()
    if not due:
        return result
    try:
        adapter = await integration_service.adapter_for(db, tenant_id, "facebook")
    except DomainError:
        result.paused = len(due)  # not connected or the token was refused: the posts wait, nothing is called
        return result
    try:
        for post in due:
            if post.fb_post_id:  # already on Facebook (a restart between the call and the commit): never post twice
                post.status, post.published_at = "published", post.published_at or now
                continue
            key = f"post-{post.id}"
            try:
                if post.image_url:
                    sent = await adapter.publish_image(post.image_url, _text(post), idempotency_key=key)
                else:
                    sent = await adapter.publish_text(_text(post), idempotency_key=key)
            except ProviderError as error:
                post.attempts += 1
                await integration_service.record_failure(db, tenant_id, "facebook", error)
                if error.needs_reconnect:
                    post.last_error = "Facebook rejected the saved token. Reconnect Facebook, then retry."
                    result.paused += 1
                    break  # the rest would be refused too
                post.last_error = "Facebook is not answering right now."
                if post.attempts >= MAX_ATTEMPTS:
                    post.status = "failed"
                    result.failed += 1
                else:
                    post.scheduled_for = now + RETRY_DELAYS[min(post.attempts - 1, len(RETRY_DELAYS) - 1)]
                    result.retried += 1
                continue
            post.fb_post_id = sent.provider_message_id
            post.status, post.published_at, post.last_error = "published", now, None
            post.attempts += 1
            result.published += 1
            record_audit(
                db,
                "marketing.post_published",
                tenant_id=tenant_id,
                actor_type="system",
                entity="marketing_post",
                entity_id=post.id,
                after={"fb_post_id": post.fb_post_id},
            )
            await integration_service.record_success(db, tenant_id, "facebook")
    finally:
        await adapter.aclose()
    await db.flush()
    return result


async def tick(now: datetime | None = None) -> TickResult:
    """One scheduler pass over every shop that has a schedule on or a post due."""
    moment = now or datetime.now(timezone.utc)
    async with system_session() as scan:
        due = set((await scan.execute(select(MarketingPost.tenant_id).where(MarketingPost.status == "queued", MarketingPost.scheduled_for <= moment))).scalars())
        scheduled = set((await scan.execute(select(MarketingSchedule.tenant_id).where(MarketingSchedule.enabled.is_(True)))).scalars())
        # shops with a recently published post (its comments may need an answer) or an approved reply waiting to go out
        commented = set(
            (
                await scan.execute(
                    select(MarketingPost.tenant_id).where(
                        MarketingPost.status == "published",
                        MarketingPost.fb_post_id.is_not(None),
                        MarketingPost.published_at >= moment - comment_reply_service.WINDOW,
                    )
                )
            ).scalars()
        )
        replying = set((await scan.execute(select(CommentReply.tenant_id).where(CommentReply.status == "approved"))).scalars())
    total = TickResult()
    for tenant_id in sorted(due | scheduled | commented | replying, key=str):
        try:
            async with tenant_session(tenant_id) as db:
                result = TickResult(generated=await generate_for_tenant(db, tenant_id, moment))
                result.add(await publish_for_tenant(db, tenant_id, moment))
                replies = await comment_reply_service.run_for_tenant(db, tenant_id, moment)
                result.replies_proposed = replies.proposed + replies.queued
                result.replies_posted = replies.posted
            total.add(result)
        except Exception:  # one shop's failure must not stop the others
            logger.exception("scheduler failed for a shop", extra={"tenant_id": str(tenant_id)})
    return total
