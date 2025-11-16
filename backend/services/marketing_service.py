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
from ..models.fb_model import ImagePostRequest, PostInsights, TextPostRequest
from ..src.exceptions import FacebookAPIError, PostCreationError

from ..lib import (
    delete_facebook_account,
    delete_marketing_post,
    get_facebook_account,
    get_schedule,
    list_facebook_accounts,
    list_marketing_posts,
    mark_schedule_triggered,
    record_marketing_post,
    save_schedule,
    update_post_insights,
    upsert_facebook_account,
)
from .inventory_service import inventory_analytics_service

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

    # ------------------------------------------------------------------
    # Scheduling utilities
    # ------------------------------------------------------------------
    def configure_schedule(
        self,
        *,
        account_id: str,
        user_id: str,
        times: List[str],
        timezone_name: str = "UTC",
    ) -> Dict[str, Any]:
        if not times:
            raise ValueError("Provide at least one posting time")
        return save_schedule(account_id=account_id, user_id=user_id, times=times, timezone_name=timezone_name)

    def fetch_schedule(self, account_id: str) -> Optional[Dict[str, Any]]:
        return get_schedule(account_id)

    # ------------------------------------------------------------------
    # Campaign orchestration
    # ------------------------------------------------------------------
    async def trigger_manual_campaign(
        self,
        *,
        account_id: str,
        user_id: str,
        prompt: Optional[str] = None,
        overrides: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        account = self._require_account(account_id)
        campaign = await self._generate_campaign(
            account=account,
            user_id=user_id,
            mode="manual",
            prompt=prompt,
            overrides=overrides or {},
        )
        return self._publish_campaign(
            account=account,
            user_id=user_id,
            campaign=campaign,
            source="manual",
            prompt=prompt,
            overrides=overrides or {},
        )

    async def trigger_scheduled_campaign(
        self,
        *,
        account_id: str,
        user_id: str,
        triggered_at: Optional[str] = None,
    ) -> Dict[str, Any]:
        account = self._require_account(account_id)
        schedule = get_schedule(account_id)
        campaign = await self._generate_campaign(
            account=account,
            user_id=user_id,
            mode="scheduled",
            prompt=None,
            overrides={"schedule": schedule},
        )
        result = self._publish_campaign(
            account=account,
            user_id=user_id,
            campaign=campaign,
            source="scheduled",
            prompt=None,
            overrides={"schedule": schedule} if schedule else {},
        )
        mark_schedule_triggered(account_id, triggered_at=triggered_at)
        return result

    def get_recent_posts(self, account_id: str, *, limit: int = 20) -> List[Dict[str, Any]]:
        return list_marketing_posts(account_id, limit=limit)

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
        response = manager.get_post_comments(facebook_post_id, limit=limit)
        data = response.model_dump()
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

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
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

        payload = {
            "account": account,
            "user_id": user_id,
            "mode": mode,
            "prompt": prompt,
            "overrides": overrides,
        }
        campaign = await self._agent_runner(payload)
        if not isinstance(campaign, dict):
            raise ValueError("Agent runner must return a mapping")
        if not campaign.get("message"):
            raise ValueError("Campaign payload requires a message")
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
        manager = self._build_manager(account)

        message = campaign.get("message", "").strip()
        hashtags = campaign.get("hashtags") or []
        angle = campaign.get("angle")
        product_sku = campaign.get("product_sku")
        image_url = campaign.get("image_url")

        if not image_url:
            image_query = self._select_image_query(
                campaign=campaign,
                prompt=prompt,
                overrides=overrides or {},
            )
            if not image_query:
                image_query = angle or product_sku or account.get("page_name")
            image_url = self._fetch_image(image_query)
            if image_url:
                campaign["image_url"] = image_url
                if image_query:
                    campaign.setdefault("image_query", image_query)

        formatted_message = self._compose_message(message=message, hashtags=hashtags)
        try:
            if image_url:
                post_request = ImagePostRequest(message=formatted_message, image_url=image_url)
                response = manager.create_image_post(post_request)
            else:
                post_request = TextPostRequest(message=formatted_message)
                response = manager.create_text_post(post_request)
        except (FacebookAPIError, PostCreationError) as exc:
            logger.error("Failed to publish marketing campaign via Facebook: %s", exc)
            raise

        record = record_marketing_post(
            account_id=account["account_id"],
            user_id=user_id,
            facebook_post_id=response.post_id,
            message=formatted_message,
            image_url=image_url,
            product_sku=product_sku,
            hashtags=hashtags,
            angle=angle,
            source=source,
            extra={"campaign": campaign},
        )
        return {"post": record, "facebook": response.model_dump()}

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
        if not query or not self._pexels_api_key:
            return None

        headers = {"Authorization": self._pexels_api_key}
        params = {"query": query, "per_page": 1, "orientation": "square"}
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

        photos = data.get("photos") or []
        if not photos:
            return None
        sources = photos[0].get("src", {})
        return sources.get("medium") or sources.get("large") or sources.get("original")

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


marketing_service = MarketingService()
