"""Domain logic for marketing automation flows."""

from __future__ import annotations

import logging
import os
import re
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable, Dict, List, Optional

import requests

from ..config.fb_config import FacebookConfig
from ..facebook_manager import FacebookManager
from ..models.fb_model import CommentReplyRequest, ImagePostRequest, PostInsights, TextPostRequest
from ..src.exceptions import FacebookAPIError, PostCreationError

from ..lib import (
    delete_facebook_account,
    delete_marketing_post,
    get_facebook_account,
    get_schedule,
    list_facebook_accounts,
    list_marketing_posts,
    mark_schedule_triggered,
    get_comment_reply,
    record_comment_reply,
    record_marketing_post,
    save_schedule,
    update_post_insights,
    upsert_facebook_account,
)
from ..lib import marketing_scheduled_repository as scheduled_repo
from ..lib import user_repository
from .inventory_service import inventory_analytics_service
from .sales_service import list_orders

logger = logging.getLogger(__name__)

PEXELS_SEARCH_ENDPOINT = "https://api.pexels.com/v1/search"
_DEFAULT_PEXELS_TIMEOUT = 10

CampaignGenerator = Callable[[Dict[str, Any]], Awaitable[Dict[str, Any]]]


class MarketingService:
    """Coordinate credential management, content generation, and publishing."""

    def __init__(
        self,
        *,
        agent_runner: Optional[CampaignGenerator] = None,
        pexels_api_key: Optional[str] = None,
        facebook_manager_factory: Optional[Callable[[FacebookConfig], FacebookManager]] = None,
        http_session: Optional[requests.Session] = None,
    ) -> None:
        self._agent_runner: CampaignGenerator
        if agent_runner is None:
            from ..my_agents.marketing_agent import generate_campaign_payload

            self._agent_runner = generate_campaign_payload
        else:
            self._agent_runner = agent_runner
        self._pexels_api_key = pexels_api_key or os.getenv("PEXELS_API_KEY") or ""
        self._facebook_manager_factory = facebook_manager_factory or self._default_manager_factory
        self._http = http_session or requests.Session()
        self._warned_missing_pexels = False
        self._auto_reply_suppressed_posts: set[str] = set()

    # ------------------------------------------------------------------
    # Account management
    # ------------------------------------------------------------------
    def register_account(
        self,
        *,
        user_id: str,
        page_id: str,
        access_token: str,
        page_name: Optional[str] = None,
        verify: bool = True,
    ) -> Dict[str, Any]:
        """Persist credentials after optional validation with Facebook."""

        page_id_clean = page_id.strip()
        access_token_clean = access_token.strip()
        if not page_id_clean or not access_token_clean:
            raise ValueError("Both page_id and access_token are required")

        if verify:
            config = self._build_config(page_id=page_id_clean, access_token=access_token_clean)
            manager = self._facebook_manager_factory(config)
            manager.verify_credentials()

        return upsert_facebook_account(
            user_id=user_id,
            page_id=page_id_clean,
            access_token=access_token_clean,
            page_name=page_name,
        )

    def remove_account(self, account_id: str) -> bool:
        return delete_facebook_account(account_id)

    def get_accounts(self, *, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        return list_facebook_accounts(user_id)

    # Small helper for development to fall back to a dev user when none
    # is provided. This keeps production behaviour unchanged while
    # allowing local workflows without a full auth stack.
    def _resolve_user_id(self, explicit: Optional[str]) -> str:
        if explicit and explicit.strip():
            return explicit.strip()

        env_default = os.getenv("BAZAARFLOW_DEV_USER_ID")
        dev = user_repository.get_default_dev_user(env_value=env_default)
        if dev and isinstance(dev.get("user_id"), str):
            return str(dev["user_id"])

        raise ValueError("Missing user_id and no dev default configured")

    # ------------------------------------------------------------------
    # Scheduling utilities
    # ------------------------------------------------------------------
    def configure_schedule(
        self,
        *,
        account_id: str,
        user_id: Optional[str],
        times: List[str],
        timezone_name: str = "UTC",
    ) -> Dict[str, Any]:
        if not times:
            raise ValueError("Provide at least one posting time")
        resolved_user_id = self._resolve_user_id(user_id)
        return save_schedule(
            account_id=account_id,
            user_id=resolved_user_id,
            times=times,
            timezone_name=timezone_name,
        )

    def fetch_schedule(self, account_id: str) -> Optional[Dict[str, Any]]:
        return get_schedule(account_id)

    # ------------------------------------------------------------------
    # Campaign orchestration
    # ------------------------------------------------------------------
    async def trigger_manual_campaign(
        self,
        *,
        account_id: str,
        user_id: Optional[str],
        prompt: Optional[str] = None,
        overrides: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        account = self._require_account(account_id)
        resolved_user_id = self._resolve_user_id(user_id)
        prepared_overrides = self._prepare_overrides(overrides)
        campaign = await self._generate_campaign(
            account=account,
            user_id=resolved_user_id,
            mode="manual",
            prompt=prompt,
            overrides=prepared_overrides,
        )
        return self._publish_campaign(
            account=account,
            user_id=resolved_user_id,
            campaign=campaign,
            source="manual",
            prompt=prompt,
            overrides=prepared_overrides,
        )

    async def trigger_scheduled_campaign(
        self,
        *,
        account_id: str,
        user_id: Optional[str],
        triggered_at: Optional[str] = None,
    ) -> Dict[str, Any]:
        account = self._require_account(account_id)
        resolved_user_id = self._resolve_user_id(user_id)
        schedule = get_schedule(account_id)
        prepared_overrides = self._prepare_overrides({"schedule": schedule} if schedule else None)
        campaign = await self._generate_campaign(
            account=account,
            user_id=resolved_user_id,
            mode="scheduled",
            prompt=None,
            overrides=prepared_overrides,
        )
        result = self._publish_campaign(
            account=account,
            user_id=resolved_user_id,
            campaign=campaign,
            source="scheduled",
            prompt=None,
            overrides=prepared_overrides,
        )
        mark_schedule_triggered(account_id, triggered_at=triggered_at)
        return result

    async def create_scheduled_campaign(
        self,
        *,
        account_id: str,
        user_id: Optional[str],
        prompt: Optional[str],
        overrides: Optional[Dict[str, Any]],
        posts_with_times: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Persist a scheduled campaign made up of already-generated posts.

        posts_with_times should be a list of dicts containing:
        - post_payload: CampaignPost-like dict from the agent
        - scheduled_at: ISO 8601 timestamp (ideally in UTC)
        """

        account = self._require_account(account_id)
        resolved_user_id = self._resolve_user_id(user_id)
        if not posts_with_times:
            raise ValueError("Provide at least one post to schedule")

        # Normalise overrides and ensure we do not mutate the caller's dict.
        prepared_overrides = self._prepare_overrides(overrides)

        now = datetime.now(timezone.utc)
        normalised_posts: List[Dict[str, Any]] = []
        for idx, item in enumerate(posts_with_times):
            payload = dict(item.get("post_payload") or {})
            scheduled_at_raw = str(item.get("scheduled_at") or "").strip()
            if not scheduled_at_raw:
                raise ValueError(f"scheduled_at is required for post index {idx}")
            try:
                scheduled_at = datetime.fromisoformat(scheduled_at_raw)
            except ValueError as exc:
                raise ValueError(f"Invalid scheduled_at for post index {idx}: {scheduled_at_raw}") from exc
            if scheduled_at.tzinfo is None:
                scheduled_at = scheduled_at.replace(tzinfo=timezone.utc)
            if scheduled_at <= now:
                raise ValueError(f"scheduled_at must be in the future for post index {idx}")

            normalised_posts.append(
                {
                    "post_payload": payload,
                    "scheduled_at": scheduled_at.isoformat(),
                }
            )

        # Use the campaign's own strategy summary if present for better UI grouping.
        strategy_summary = None
        if normalised_posts:
            first_payload = normalised_posts[0]["post_payload"]
            raw_campaign = first_payload.get("raw_campaign") if isinstance(first_payload, dict) else None
            if isinstance(raw_campaign, dict):
                summary_candidate = raw_campaign.get("strategy_summary")
                if isinstance(summary_candidate, str):
                    strategy_summary = summary_candidate

        created = scheduled_repo.create_scheduled_campaign(
            account_id=account["account_id"],
            user_id=resolved_user_id,
            prompt=prompt,
            strategy_summary=strategy_summary,
            overrides=prepared_overrides,
            posts_with_times=normalised_posts,
        )
        return created

    def publish_scheduled_post(self, *, scheduled_post_id: str) -> Dict[str, Any]:
        """Publish a single scheduled post and update its status.

        This reuses the same Facebook and Pexels logic as _publish_campaign
        but operates on a ScheduledPost record.
        """

        record = scheduled_repo.get_scheduled_post(scheduled_post_id=scheduled_post_id)
        if not record:
            raise ValueError(f"No scheduled post found for id {scheduled_post_id}")

        if record.get("status") != "pending":
            raise ValueError(f"Scheduled post {scheduled_post_id} is not pending")

        account = self._require_account(record["account_id"])
        manager = self._build_manager(account)

        post_payload = dict(record.get("post_payload") or {})

        message = (post_payload.get("message") or "").strip()
        hashtags = post_payload.get("hashtags") or []
        product_sku = post_payload.get("product_sku")
        call_to_action = (post_payload.get("call_to_action") or "").strip() or None
        image_url = post_payload.get("image_url")
        image_query = post_payload.get("image_query")

        if not image_url:
            resolved_query = image_query or self._select_image_query(
                campaign=post_payload,
                prompt=None,
                overrides=record.get("overrides") or {},
            )
            image_url = self._fetch_image(resolved_query)
            if image_url:
                post_payload["image_url"] = image_url
                if resolved_query:
                    post_payload.setdefault("image_query", resolved_query)

        if call_to_action:
            message_with_cta = f"{message}\n\n{call_to_action}" if message else call_to_action
        else:
            message_with_cta = message

        formatted_message = self._compose_message(message=message_with_cta, hashtags=hashtags)

        try:
            if image_url:
                post_request = ImagePostRequest(message=formatted_message, image_url=image_url)
                response = manager.create_image_post(post_request)
            else:
                post_request = TextPostRequest(message=formatted_message)
                response = manager.create_text_post(post_request)
        except (FacebookAPIError, PostCreationError) as exc:
            logger.error("Failed to publish scheduled marketing post via Facebook: %s", exc)
            scheduled_repo.mark_scheduled_post_failed(scheduled_post_id=scheduled_post_id, error=str(exc))
            raise

        record_post = record_marketing_post(
            account_id=record["account_id"],
            user_id=record["user_id"],
            facebook_post_id=response.post_id,
            message=formatted_message,
            image_url=image_url,
            product_sku=product_sku,
            hashtags=hashtags,
            angle=post_payload.get("title"),
            source="scheduled_campaign",
            extra={
                "scheduled_campaign_id": record["scheduled_campaign_id"],
                "scheduled_post_id": scheduled_post_id,
                "scheduled_at": record.get("scheduled_at"),
            },
        )

        scheduled_repo.mark_scheduled_post_posted(
            scheduled_post_id=scheduled_post_id,
            facebook_post_id=response.post_id,
        )

        return {
            "facebook": response.model_dump(),
            "post": record_post,
        }

    def get_recent_posts(self, account_id: str, *, limit: int = 20) -> List[Dict[str, Any]]:
        posts = list_marketing_posts(account_id, limit=limit)

        if not posts:
            return posts

        try:
            account = self._require_account(account_id)
        except ValueError:
            return posts

        manager = self._build_manager(account)

        for post in posts:
            facebook_post_id = post.get("facebook_post_id")
            if not isinstance(facebook_post_id, str):
                continue
            if facebook_post_id in self._auto_reply_suppressed_posts:
                continue
            if "_" not in facebook_post_id:
                logger.debug("Skipping auto-reply for non feed-style post id %s", facebook_post_id)
                self._auto_reply_suppressed_posts.add(facebook_post_id)
                continue
            try:
                self._auto_reply_recent_comments(
                    manager=manager,
                    account_id=account_id,
                    facebook_post_id=facebook_post_id,
                    limit=5,
                )
            except FacebookAPIError as exc:
                if self._is_permission_or_missing_error(exc):
                    logger.warning(
                        "Suppressing auto-reply for post %s due to Facebook permissions/missing content: %s",
                        facebook_post_id,
                        exc,
                    )
                    self._auto_reply_suppressed_posts.add(facebook_post_id)
                else:
                    logger.debug(
                        "Skipping auto-reply for post %s due to API error: %s",
                        facebook_post_id,
                        exc,
                    )

        return posts

    def list_scheduled_activity(self, account_id: str) -> Dict[str, Any]:
        """Return scheduled posts for an account for activity views.

        Posts are sorted by their scheduled_at timestamp in ascending
        order so that the next posts to go out appear first.
        """

        records = scheduled_repo.list_scheduled_posts_for_account(account_id=account_id)
        # Sort by scheduled_at as ISO 8601 strings; invalid or missing
        # values fall to the end.
        def _sort_key(record: Dict[str, Any]) -> str:
            value = record.get("scheduled_at")
            return value if isinstance(value, str) else "\uffff"

        ordered = sorted(records, key=_sort_key)
        return {"posts": ordered}

    def update_scheduled_post(
        self,
        *,
        scheduled_post_id: str,
        post_payload: Optional[Dict[str, Any]] = None,
        scheduled_at: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Update a pending scheduled post's payload and/or scheduled time.

        Only posts in the pending state are editable. scheduled_at must be a
        valid ISO 8601 timestamp in the future.
        """

        record = scheduled_repo.get_scheduled_post(scheduled_post_id=scheduled_post_id)
        if not record:
            raise ValueError(f"No scheduled post found for id {scheduled_post_id}")

        if record.get("status") != "pending":
            raise ValueError("Only pending scheduled posts can be edited")

        updates: Dict[str, Any] = {}

        if scheduled_at is not None:
            scheduled_at_str = str(scheduled_at).strip()
            if not scheduled_at_str:
                raise ValueError("scheduled_at cannot be empty")
            try:
                parsed = datetime.fromisoformat(scheduled_at_str)
            except ValueError as exc:
                raise ValueError(f"Invalid scheduled_at value: {scheduled_at_str}") from exc
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            now = datetime.now(timezone.utc)
            if parsed <= now:
                raise ValueError("scheduled_at must be in the future")
            updates["scheduled_at"] = parsed.isoformat()

        if post_payload is not None:
            if not isinstance(post_payload, dict):
                raise ValueError("post_payload must be an object")
            updates["post_payload"] = post_payload

        updated = scheduled_repo.update_scheduled_post(
            scheduled_post_id=scheduled_post_id,
            updates=updates,
        )
        if not updated:
            raise ValueError(f"Scheduled post {scheduled_post_id} could not be updated")

        return updated

    def update_scheduled_campaign(
        self,
        *,
        scheduled_campaign_id: str,
        strategy_summary: Optional[str] = None,
        status: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Update simple metadata for a scheduled campaign."""

        updates: Dict[str, Any] = {}
        if strategy_summary is not None:
            updates["strategy_summary"] = strategy_summary
        if status is not None:
            updates["status"] = status

        if not updates:
            raise ValueError("No fields to update")

        updated = scheduled_repo.update_scheduled_campaign(
            scheduled_campaign_id=scheduled_campaign_id,
            updates=updates,
        )
        if not updated:
            raise ValueError(f"Scheduled campaign {scheduled_campaign_id} not found")

        return updated

    def delete_scheduled_post(self, *, scheduled_post_id: str) -> bool:
        """Delete a scheduled post from the queue.

        This does not affect any already-published Facebook content; it simply
        removes the pending record so it will not be picked up by the
        scheduler.
        """

        record = scheduled_repo.get_scheduled_post(scheduled_post_id=scheduled_post_id)
        if not record:
            raise ValueError(f"No scheduled post found for id {scheduled_post_id}")
        if record.get("status") != "pending":
            raise ValueError("Only pending scheduled posts can be deleted")

        removed = scheduled_repo.delete_scheduled_post(scheduled_post_id=scheduled_post_id)
        if not removed:
          raise ValueError(f"Scheduled post {scheduled_post_id} could not be deleted")
        return True

    def delete_scheduled_campaign(self, *, scheduled_campaign_id: str) -> bool:
        """Delete a scheduled campaign and all its posts."""

        removed = scheduled_repo.delete_scheduled_campaign(scheduled_campaign_id=scheduled_campaign_id)
        if not removed:
            raise ValueError(f"Scheduled campaign {scheduled_campaign_id} not found")
        return True

    def refresh_post_insights(self, *, account_id: str, facebook_post_id: str) -> Optional[Dict[str, Any]]:
        account = self._require_account(account_id)
        manager = self._build_manager(account)
        insights = manager.get_post_insights(facebook_post_id)
        payload = self._insights_to_dict(insights)
        return update_post_insights(account_id=account_id, facebook_post_id=facebook_post_id, insights=payload)

    def get_post_comments(self, *, account_id: str, facebook_post_id: str, limit: int = 50) -> Dict[str, Any]:
        """Fetch comments for a marketing post directly from Facebook."""

        if limit <= 0:
            raise ValueError("limit must be greater than zero")
        account = self._require_account(account_id)
        manager = self._build_manager(account)
        try:
            response = manager.get_post_comments(facebook_post_id, limit=limit)
        except FacebookAPIError as exc:
            if self._is_permission_or_missing_error(exc):
                logger.warning(
                    "Facebook permissions prevented comment fetch for post %s: %s",
                    facebook_post_id,
                    exc,
                )
                return {
                    "comments": [],
                    "total_count": 0,
                    "has_next_page": False,
                    "next_cursor": None,
                    "keywords": None,
                    "fetched_at": datetime.now(timezone.utc).isoformat(),
                }
            raise
        data = response.model_dump()

        comments = data.get("comments", [])
        try:
            enriched_comments = self._auto_reply_to_comments(
                manager=manager,
                account_id=account_id,
                facebook_post_id=facebook_post_id,
                comments=comments,
            )
        except FacebookAPIError as exc:
            logger.debug(
                "Auto reply failed during comment fetch for post %s: %s",
                facebook_post_id,
                exc,
            )
            enriched_comments = comments

        if enriched_comments is not None:
            data["comments"] = enriched_comments

        data["fetched_at"] = datetime.now(timezone.utc).isoformat()
        return data

    def delete_post(
        self,
        *,
        account_id: str,
        facebook_post_id: str,
        remove_remote: bool = True,
    ) -> Dict[str, Any]:
        """Delete a marketing post from storage and optionally Facebook."""

        account = self._require_account(account_id)
        removed_remote: Optional[bool] = None
        if remove_remote:
            manager = self._build_manager(account)
            removed_remote = manager.delete_post(facebook_post_id)

        removed_local = delete_marketing_post(account_id=account_id, facebook_post_id=facebook_post_id)
        return {
            "removed_remote": removed_remote,
            "removed_local": removed_local,
        }

    def reply_to_comment(
        self,
        *,
        account_id: str,
        facebook_post_id: str,
        comment_id: str,
        comment_message: Optional[str] = None,
        commenter_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Reply to a Facebook comment with a tailored WhatsApp handoff."""

        if not comment_id:
            raise ValueError("comment_id is required")

        account = self._require_account(account_id)
        manager = self._build_manager(account)

        reply_text = self._compose_whatsapp_reply(
            comment_id=comment_id,
            facebook_post_id=facebook_post_id,
            comment_message=comment_message,
            commenter_name=commenter_name,
        )

        request = CommentReplyRequest(comment_id=comment_id, message=reply_text)
        action = manager.reply_to_comment(request)
        record = record_comment_reply(
            account_id=account_id,
            facebook_post_id=facebook_post_id,
            comment_id=comment_id,
            reply_text=reply_text,
        )

        return {
            "comment_id": comment_id,
            "reply": reply_text,
            "action": action.model_dump(),
            "reply_metadata": {
                "reply_text": record.get("reply_text", reply_text),
                "replied_at": record.get("replied_at"),
            },
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _prepare_overrides(self, overrides: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        merged: Dict[str, Any] = {**(overrides or {})}
        merged.setdefault("operational_context", self._compose_operational_context())
        return merged

    def _compose_operational_context(self) -> Dict[str, Any]:
        try:
            stock_health = inventory_analytics_service.get_stock_health()
            stock_detail = inventory_analytics_service.get_stock_health_detail()
            low_stock_items = list(stock_detail.get("low_stock", {}).get("items", []))[:5]
            restock_queue = inventory_analytics_service.get_restock_queue(limit=5)
        except Exception as exc:  # pragma: no cover - defensive guard around IO
            logger.warning("Unable to collect inventory analytics: %s", exc)
            stock_health = {}
            low_stock_items = []
            restock_queue = []

        try:
            orders = list_orders()
        except Exception as exc:  # pragma: no cover - defensive guard around IO
            logger.warning("Unable to load sales orders: %s", exc)
            orders = []

        product_totals: Dict[str, int] = {}
        for order in orders:
            name = (order.get("product_name") or "").strip()
            if not name:
                continue
            product_totals[name] = product_totals.get(name, 0) + int(order.get("quantity", 1) or 1)

        top_requested = [
            {"product_name": product, "orders": count}
            for product, count in sorted(product_totals.items(), key=lambda item: item[1], reverse=True)[:5]
        ]

        recent_orders = [
            {
                "product_name": order.get("product_name"),
                "quantity": order.get("quantity"),
                "payment_status": order.get("payment_status"),
                "customer": order.get("customer_name"),
            }
            for order in orders[-5:]
        ]

        return {
            "inventory": {
                "stock_health": stock_health,
                "low_stock_watchlist": low_stock_items,
                "restock_queue": restock_queue,
            },
            "sales": {
                "total_orders": len(orders),
                "top_requested_products": top_requested,
                "recent_orders": recent_orders,
            },
        }

    async def _generate_campaign(
        self,
        *,
        account: Dict[str, Any],
        user_id: str,
        mode: str,
        prompt: Optional[str],
        overrides: Dict[str, Any],
    ) -> Dict[str, Any]:
        if not self._agent_runner:
            raise RuntimeError("Marketing agent runner is not configured")

        # Extract an optional post_count hint from overrides, clamped to a safe range.
        raw_post_count = overrides.get("post_count") if isinstance(overrides, dict) else None
        try:
            post_count_hint = int(raw_post_count) if raw_post_count is not None else None
        except (TypeError, ValueError):
            post_count_hint = None

        if post_count_hint is not None:
            post_count_hint = max(1, min(post_count_hint, 6))

        payload = {
            "account": account,
            "user_id": user_id,
            "mode": mode,
            "prompt": prompt,
            "overrides": overrides,
        }
        # Surface the post_count hint in the payload the agent sees so it can honour it.
        if post_count_hint is not None:
            payload["post_count"] = post_count_hint
        campaign = await self._agent_runner(payload)
        if not isinstance(campaign, dict):
            raise ValueError("Agent runner must return a mapping")

        # Expect a campaign payload shaped like CampaignResponse
        posts = campaign.get("posts")
        if not isinstance(posts, list) or not posts:
            raise ValueError("Marketing agent must return at least one post in the campaign")

        if len(posts) > 6:
            raise ValueError("Marketing agent must not return more than 6 posts in the campaign")

        if post_count_hint is not None and len(posts) != post_count_hint:
            raise ValueError("Marketing agent did not honour the requested post_count")

        return campaign

    def _publish_campaign(
        self,
        *,
        account: Dict[str, Any],
        user_id: str,
        campaign: Dict[str, Any],
        source: str,
        prompt: Optional[str],
        overrides: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Publish all posts for a generated campaign.

        The campaign payload is expected to follow the CampaignResponse
        structure returned by the marketing agent:

        {
            "strategy_summary": "...",
            "posts": [
                {
                    "title": "...",
                    "message": "...",
                    "hashtags": ["..."],
                    "image_query": "...",
                    "image_url": null,
                    "product_sku": null,
                    "call_to_action": "...",
                    "day_offset": 0
                },
                ...
            ]
        }
        """

        manager = self._build_manager(account)

        strategy_summary = campaign.get("strategy_summary")
        posts = campaign.get("posts") or []
        if not isinstance(posts, list) or not posts:
            raise ValueError("Campaign payload must include a non-empty 'posts' array")

        # Use a shared campaign identifier so posts can be grouped later in the UI.
        campaign_id = campaign.get("campaign_id") or f"cmp_{account.get('account_id')}_{datetime.now(timezone.utc).isoformat()}"

        published_posts: List[Dict[str, Any]] = []
        for idx, post in enumerate(posts):
            if not isinstance(post, dict):
                logger.warning("Skipping malformed campaign post at index %s: %r", idx, post)
                continue

            # Per-post fields coming from the agent
            message = (post.get("message") or "").strip()
            hashtags = post.get("hashtags") or []
            product_sku = post.get("product_sku")
            call_to_action = (post.get("call_to_action") or "").strip() or None
            image_url = post.get("image_url")
            image_query = post.get("image_query")

            # If the agent did not supply an image_url, resolve via Pexels using
            # the explicit image_query first, then fall back to legacy inference.
            if not image_url:
                resolved_query = image_query or self._select_image_query(
                    campaign=post,
                    prompt=prompt,
                    overrides=overrides or {},
                )
                image_url = self._fetch_image(resolved_query)
                if image_url:
                    post["image_url"] = image_url
                    if resolved_query:
                        post.setdefault("image_query", resolved_query)

            # Compose final message by appending CTA and hashtags.
            if call_to_action:
                message_with_cta = f"{message}\n\n{call_to_action}" if message else call_to_action
            else:
                message_with_cta = message

            formatted_message = self._compose_message(message=message_with_cta, hashtags=hashtags)

            try:
                if image_url:
                    post_request = ImagePostRequest(message=formatted_message, image_url=image_url)
                    response = manager.create_image_post(post_request)
                else:
                    post_request = TextPostRequest(message=formatted_message)
                    response = manager.create_text_post(post_request)
            except (FacebookAPIError, PostCreationError) as exc:
                logger.error("Failed to publish marketing campaign post via Facebook: %s", exc)
                raise

            record = record_marketing_post(
                account_id=account["account_id"],
                user_id=user_id,
                facebook_post_id=response.post_id,
                message=formatted_message,
                image_url=image_url,
                product_sku=product_sku,
                hashtags=hashtags,
                angle=post.get("title"),
                source=source,
                extra={
                    "campaign_id": campaign_id,
                    "strategy_summary": strategy_summary,
                    "campaign_post_index": idx,
                    "raw_campaign": campaign,
                },
            )

            published_posts.append({
                "facebook": response.model_dump(),
                "post": record,
            })

        return {
            "campaign_id": campaign_id,
            "strategy_summary": strategy_summary,
            "posts": published_posts,
        }

    def _select_image_query(
        self,
        *,
        campaign: Dict[str, Any],
        prompt: Optional[str],
        overrides: Dict[str, Any],
    ) -> Optional[str]:
        explicit_query = campaign.get("image_query") or overrides.get("image_query")
        if explicit_query:
            return str(explicit_query)

        sku = campaign.get("product_sku") or overrides.get("product_sku")
        if sku:
            item = inventory_analytics_service.get_item_by_sku(str(sku))
            if item and item.get("name"):
                return f"{item['name']} product photo"

        product_name = campaign.get("product_name") or overrides.get("product_name")
        if product_name:
            return f"{product_name} product photo"

        inferred = self._infer_product_from_text(prompt) if prompt else None
        if inferred:
            return f"{inferred} product photo"

        hashtags = campaign.get("hashtags") or []
        for tag in hashtags:
            cleaned = str(tag).lstrip("#").strip()
            if cleaned and self._matches_inventory_product(cleaned):
                return f"{cleaned} product photo"

        message = campaign.get("message")
        if isinstance(message, str):
            inferred_from_message = self._infer_product_from_text(message)
            if inferred_from_message:
                return f"{inferred_from_message} product photo"

        return None

    def _infer_product_from_text(self, text: str) -> Optional[str]:
        if not text:
            return None
        text_lower = text.lower()
        items = inventory_analytics_service.get_all_items()
        for item in items:
            name = item.get("name")
            if name and name.lower() in text_lower:
                return name

        tokens = re.findall(r"[a-z0-9]+", text_lower)
        for token in tokens:
            matches = inventory_analytics_service.search_items(token, limit=1)
            if matches:
                candidate = matches[0].get("name")
                if candidate:
                    return candidate
        return None

    def _matches_inventory_product(self, candidate: str) -> bool:
        if not candidate:
            return False
        candidate_normalized = candidate.lower().replace(" ", "")
        items = inventory_analytics_service.get_all_items()
        for item in items:
            name = item.get("name")
            if name and name.lower().replace(" ", "") == candidate_normalized:
                return True
        matches = inventory_analytics_service.search_items(candidate, limit=1)
        return bool(matches)

    def _fetch_image(self, query: Optional[str]) -> Optional[str]:
        if not query:
            return None
        if not self._pexels_api_key:
            if not self._warned_missing_pexels:
                logger.warning("Skipping Pexels lookup because no API key is configured")
                self._warned_missing_pexels = True
            return None

        headers = {"Authorization": self._pexels_api_key}
        params = {
            "query": query,
            "per_page": int(os.getenv("PEXELS_RESULT_WINDOW", "4")),
            "orientation": os.getenv("PEXELS_ORIENTATION", "landscape"),
            "size": os.getenv("PEXELS_SIZE", "large"),
        }
        try:
            response = self._http.get(
                PEXELS_SEARCH_ENDPOINT,
                headers=headers,
                params=params,
                timeout=_DEFAULT_PEXELS_TIMEOUT,
            )
            response.raise_for_status()
            data = response.json()
        except (requests.RequestException, ValueError) as exc:
            logger.warning("Pexels search failed for query '%s': %s", query, exc)
            return None

        photos = [photo for photo in data.get("photos") or [] if self._photo_is_usable(photo)]
        if not photos:
            logger.info("No suitable Pexels photo found for query '%s'", query)
            return None
        preferred_sources = ("large2x", "large", "medium", "original")
        for source_name in preferred_sources:
            candidate = photos[0].get("src", {}).get(source_name)
            if candidate:
                return candidate
        return None

    def _photo_is_usable(self, photo: Dict[str, Any]) -> bool:
        width = int(photo.get("width") or 0)
        height = int(photo.get("height") or 0)
        has_src = isinstance(photo.get("src"), dict)
        return width >= 1200 and height >= 800 and has_src

    def _compose_message(self, *, message: str, hashtags: List[str]) -> str:
        normalized_tags = [tag if tag.startswith("#") else f"#{tag}" for tag in hashtags if tag]
        if normalized_tags:
            hashtags_block = " ".join(sorted(set(normalized_tags)))
            if message:
                return f"{message}\n\n{hashtags_block}"
            return hashtags_block
        return message

    def _build_manager(self, account: Dict[str, Any]) -> FacebookManager:
        config = self._build_config(page_id=account["page_id"], access_token=account["access_token"])
        return self._facebook_manager_factory(config)

    def _build_config(self, *, page_id: str, access_token: str) -> FacebookConfig:
        kwargs = {
            "facebook_page_id": page_id,
            "facebook_access_token": access_token,
            "facebook_api_version": os.getenv("FACEBOOK_API_VERSION", "v24.0"),
            "facebook_api_base_url": os.getenv("FACEBOOK_API_BASE_URL", "https://graph.facebook.com"),
            "request_timeout": int(os.getenv("REQUEST_TIMEOUT", "30")),
            "max_retries": int(os.getenv("MAX_RETRIES", "3")),
        }
        return FacebookConfig(**kwargs)

    def _default_manager_factory(self, config: FacebookConfig) -> FacebookManager:
        return FacebookManager(config=config)

    def _insights_to_dict(self, insights: PostInsights) -> Dict[str, Any]:
        data = insights.model_dump()
        data["retrieved_at"] = datetime.now(timezone.utc).isoformat()
        return data

    def _require_account(self, account_id: str) -> Dict[str, Any]:
        account = get_facebook_account(account_id)
        if not account:
            raise ValueError(f"No marketing credentials stored for account_id {account_id}")
        return account

    def _auto_reply_recent_comments(
        self,
        *,
        manager: FacebookManager,
        account_id: str,
        facebook_post_id: str,
        limit: int = 5,
    ) -> None:
        try:
            response = manager.get_post_comments(facebook_post_id, limit=limit)
        except FacebookAPIError as exc:
            if self._is_permission_or_missing_error(exc):
                logger.debug(
                    "Auto-reply suppressed during fetch for post %s: %s",
                    facebook_post_id,
                    exc,
                )
                self._auto_reply_suppressed_posts.add(facebook_post_id)
                return
            raise
        comments = response.model_dump().get("comments", [])
        self._auto_reply_to_comments(
            manager=manager,
            account_id=account_id,
            facebook_post_id=facebook_post_id,
            comments=comments,
        )

    def _auto_reply_to_comments(
        self,
        *,
        manager: FacebookManager,
        account_id: str,
        facebook_post_id: str,
        comments: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        if not comments:
            return list(comments)

        page_id = getattr(manager.config, "facebook_page_id", None)
        hydrated: List[Dict[str, Any]] = []

        for raw_comment in comments:
            if isinstance(raw_comment, dict):
                comment = dict(raw_comment)
            elif hasattr(raw_comment, "model_dump"):
                comment = raw_comment.model_dump()
            else:
                logger.debug("Unrecognised comment payload type: %s", type(raw_comment))
                continue
            comment_id = comment.get("comment_id") or comment.get("id")
            if not comment_id:
                hydrated.append(comment)
                continue

            if comment.get("parent_comment_id"):
                hydrated.append(comment)
                continue

            from_user = comment.get("from_user") or {}
            author_id = from_user.get("id") or from_user.get("uid")
            if page_id and author_id == page_id:
                hydrated.append(comment)
                continue

            stored_reply = get_comment_reply(
                account_id=account_id,
                facebook_post_id=facebook_post_id,
                comment_id=str(comment_id),
            )
            if stored_reply:
                comment["reply_metadata"] = {
                    "reply_text": stored_reply.get("reply_text"),
                    "replied_at": stored_reply.get("replied_at"),
                }
                hydrated.append(comment)
                continue

            commenter_name = from_user.get("name") or from_user.get("username")
            reply_text = self._compose_whatsapp_reply(
                comment_id=str(comment_id),
                facebook_post_id=facebook_post_id,
                comment_message=comment.get("message"),
                commenter_name=commenter_name,
            )

            try:
                manager.reply_to_comment(CommentReplyRequest(comment_id=str(comment_id), message=reply_text))
            except FacebookAPIError as exc:
                if self._is_permission_or_missing_error(exc):
                    logger.debug(
                        "Suppressing further auto-replies for post %s after permission error on comment %s",
                        facebook_post_id,
                        comment_id,
                    )
                    self._auto_reply_suppressed_posts.add(facebook_post_id)
                    hydrated.append(comment)
                    continue
                logger.debug("Auto reply failed for comment %s: %s", comment_id, exc)
                hydrated.append(comment)
                continue

            record = record_comment_reply(
                account_id=account_id,
                facebook_post_id=facebook_post_id,
                comment_id=str(comment_id),
                reply_text=reply_text,
            )
            comment["reply_metadata"] = {
                "reply_text": record.get("reply_text", reply_text),
                "replied_at": record.get("replied_at"),
            }
            hydrated.append(comment)

        return hydrated

    def _compose_whatsapp_reply(
        self,
        *,
        comment_id: str,
        facebook_post_id: Optional[str],
        comment_message: Optional[str],
        commenter_name: Optional[str],
    ) -> str:
        number = "+1 (555) 160-3580"
        first_name: Optional[str] = None
        if commenter_name:
            tokens = commenter_name.strip().split()
            if tokens:
                first_name = tokens[0]

        greeting_name = first_name or "there"
        topic = self._extract_topic_from_comment(comment_message)

        templates = [
            lambda g, t: f"Thanks, {g}! We'd love to help with {t}. Message us on WhatsApp at {number} so we can share everything.",
            lambda g, t: f"Hi {g}! Let's continue this on WhatsApp for the full details. Send us a quick message at {number}.",
            lambda g, t: f"Hey {g}, appreciate your comment. WhatsApp us at {number} and we'll walk you through it.",
            lambda g, t: f"{g.capitalize()}, thanks for reaching out. Our team replies fastest on WhatsApp—drop us a note at {number}.",
            lambda g, t: f"Great to hear from you, {g}! For everything about {t}, ping us on WhatsApp at {number} and we'll help right away.",
        ]

        selector_basis = f"{comment_id}:{facebook_post_id or ''}:{comment_message or ''}"
        index = abs(hash(selector_basis)) % len(templates)
        template = templates[index]
        return template(greeting_name, topic)

    def _extract_topic_from_comment(self, comment_message: Optional[str]) -> str:
        if not comment_message:
            return "what you're looking for"

        cleaned = re.sub(r"https?://\S+", "", comment_message)
        words = re.findall(r"[A-Za-z0-9']+", cleaned)
        meaningful = [word for word in words if len(word) > 3]

        if meaningful:
            phrase = " ".join(meaningful[:2])
        elif words:
            phrase = " ".join(words[:2])
        else:
            return "what you're looking for"

        phrase = phrase.lower().strip()
        if not phrase:
            return "what you're looking for"
        return phrase

    def _is_permission_or_missing_error(self, error: FacebookAPIError) -> bool:
        return error.error_code in {10, 100}


marketing_service = MarketingService()
