"""JSON-backed storage for scheduled marketing campaigns and posts.

This module keeps things simple and consistent with the existing JSON stores
used elsewhere in the project. It is intentionally minimal and focused on the
operations needed by the marketing scheduler.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .json_store import JsonStore


_SCHEDULED_CAMPAIGNS_PATH = "db/marketing_scheduled_campaigns.json"
_SCHEDULED_POSTS_PATH = "db/marketing_scheduled_posts.json"


@dataclass
class ScheduledCampaign:
    scheduled_campaign_id: str
    account_id: str
    user_id: str
    prompt: Optional[str]
    strategy_summary: Optional[str]
    overrides: Dict[str, Any]
    created_at: str
    status: str  # draft | scheduled | partially_posted | completed


@dataclass
class ScheduledPost:
    scheduled_post_id: str
    scheduled_campaign_id: str
    account_id: str
    user_id: str
    campaign_post_index: int
    post_payload: Dict[str, Any]
    scheduled_at: str  # ISO 8601 in UTC
    status: str  # pending | posted | cancelled | failed
    facebook_post_id: Optional[str] = None
    error: Optional[str] = None


_campaign_store = JsonStore(_SCHEDULED_CAMPAIGNS_PATH, default_factory=list)
_post_store = JsonStore(_SCHEDULED_POSTS_PATH, default_factory=list)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def create_scheduled_campaign(
    *,
    account_id: str,
    user_id: str,
    prompt: Optional[str],
    strategy_summary: Optional[str],
    overrides: Optional[Dict[str, Any]],
    posts_with_times: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Create a scheduled campaign and its associated scheduled posts.

    posts_with_times is a list of dicts with keys:
    - post_payload: the agent-generated post content (CampaignPost-like)
    - scheduled_at: ISO 8601 string in UTC
    """

    overrides_clean: Dict[str, Any] = {**(overrides or {})}

    scheduled_campaign_id = f"scmp_{account_id}_{int(datetime.now(timezone.utc).timestamp())}"
    campaign = ScheduledCampaign(
        scheduled_campaign_id=scheduled_campaign_id,
        account_id=account_id,
        user_id=user_id,
        prompt=prompt,
        strategy_summary=strategy_summary,
        overrides=overrides_clean,
        created_at=_now_iso(),
        status="scheduled",
    )
    def _upsert_campaign(row: list[Dict[str, Any]]) -> tuple[list[Dict[str, Any]], Dict[str, Any]]:
        rows = list(row or [])
        # Replace any existing campaign with same id, else append
        next_rows: list[Dict[str, Any]] = []
        for existing in rows:
            if existing.get("scheduled_campaign_id") == scheduled_campaign_id:
                continue
            next_rows.append(existing)
        next_rows.append(asdict(campaign))
        return next_rows, asdict(campaign)

    _campaign_store.update(_upsert_campaign)

    scheduled_posts: List[Dict[str, Any]] = []
    for index, item in enumerate(posts_with_times):
        post_payload = dict(item.get("post_payload") or {})
        scheduled_at = str(item.get("scheduled_at") or "").strip()
        if not scheduled_at:
            raise ValueError("scheduled_at is required for each scheduled post")

        scheduled_post_id = f"sp_{scheduled_campaign_id}_{index}"
        record = ScheduledPost(
            scheduled_post_id=scheduled_post_id,
            scheduled_campaign_id=scheduled_campaign_id,
            account_id=account_id,
            user_id=user_id,
            campaign_post_index=index,
            post_payload=post_payload,
            scheduled_at=scheduled_at,
            status="pending",
        )
        def _upsert_post(rows: list[Dict[str, Any]]) -> tuple[list[Dict[str, Any]], Dict[str, Any]]:
            current = list(rows or [])
            next_rows: list[Dict[str, Any]] = []
            for existing in current:
                if existing.get("scheduled_post_id") == scheduled_post_id:
                    continue
                next_rows.append(existing)
            row_dict = asdict(record)
            next_rows.append(row_dict)
            return next_rows, row_dict

        _post_store.update(_upsert_post)
        scheduled_posts.append(asdict(record))

    return {
        "campaign": asdict(campaign),
        "posts": scheduled_posts,
    }


def list_pending_scheduled_posts(*, now_iso: Optional[str] = None) -> List[Dict[str, Any]]:
    """Return all scheduled posts that are pending and due at or before now.

    This function is intentionally simple. The caller is responsible for
    applying any additional time windows if desired.
    """

    if now_iso is None:
        now_iso = _now_iso()
    try:
        now = datetime.fromisoformat(now_iso)
    except ValueError:
        now = datetime.now(timezone.utc)

    data = _post_store.read() or []
    if not isinstance(data, list):
        return []

    results: List[Dict[str, Any]] = []
    for record in data:
        if record.get("status") != "pending":
            continue
        scheduled_at_str = record.get("scheduled_at")
        if not isinstance(scheduled_at_str, str):
            continue
        try:
            scheduled_at = datetime.fromisoformat(scheduled_at_str)
        except ValueError:
            continue
        if scheduled_at.tzinfo is None:
            scheduled_at = scheduled_at.replace(tzinfo=timezone.utc)
        if scheduled_at <= now:
            results.append(record)
    return results


def mark_scheduled_post_posted(*, scheduled_post_id: str, facebook_post_id: str) -> Optional[Dict[str, Any]]:
    def _mutator(rows: list[Dict[str, Any]]) -> tuple[list[Dict[str, Any]], Optional[Dict[str, Any]]]:
        current = list(rows or [])
        updated: Optional[Dict[str, Any]] = None
        next_rows: list[Dict[str, Any]] = []
        for existing in current:
            if existing.get("scheduled_post_id") == scheduled_post_id:
                updated = dict(existing)
                updated["status"] = "posted"
                updated["facebook_post_id"] = facebook_post_id
                updated["error"] = None
                next_rows.append(updated)
            else:
                next_rows.append(existing)
        return next_rows, updated

    return _post_store.update(_mutator)


def mark_scheduled_post_failed(*, scheduled_post_id: str, error: str) -> Optional[Dict[str, Any]]:
    def _mutator(rows: list[Dict[str, Any]]) -> tuple[list[Dict[str, Any]], Optional[Dict[str, Any]]]:
        current = list(rows or [])
        updated: Optional[Dict[str, Any]] = None
        next_rows: list[Dict[str, Any]] = []
        for existing in current:
            if existing.get("scheduled_post_id") == scheduled_post_id:
                updated = dict(existing)
                updated["status"] = "failed"
                updated["error"] = error
                next_rows.append(updated)
            else:
                next_rows.append(existing)
        return next_rows, updated

    return _post_store.update(_mutator)


def get_scheduled_post(*, scheduled_post_id: str) -> Optional[Dict[str, Any]]:
    data = _post_store.read() or []
    if not isinstance(data, list):
        return None
    for record in data:
        if record.get("scheduled_post_id") == scheduled_post_id:
            return record
    return None


def list_scheduled_posts_for_account(*, account_id: str) -> List[Dict[str, Any]]:
    """Return all scheduled posts for a given account.

    This is used by the marketing activity view to surface the queued
    posts. Callers can apply additional filtering (e.g. by status) if
    desired.
    """

    data = _post_store.read() or []
    if not isinstance(data, list):
        return []
    return [record for record in data if record.get("account_id") == account_id]


def update_scheduled_post(*, scheduled_post_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Apply a limited set of updates to a scheduled post.

    Only safe, whitelisted fields are updated. If the post is not found or is
    no longer pending, this function returns None.
    """

    allowed_top_level = {"scheduled_at"}
    allowed_payload_fields = {"message", "hashtags", "call_to_action", "image_url", "product_sku"}

    def _mutator(rows: list[Dict[str, Any]]) -> tuple[list[Dict[str, Any]], Optional[Dict[str, Any]]]:
        current = list(rows or [])
        updated: Optional[Dict[str, Any]] = None
        next_rows: list[Dict[str, Any]] = []

        for existing in current:
            if existing.get("scheduled_post_id") != scheduled_post_id:
                next_rows.append(existing)
                continue

            # Only pending posts can be edited
            if existing.get("status") != "pending":
                next_rows.append(existing)
                continue

            record = dict(existing)

            for key, value in updates.items():
                if key in allowed_top_level:
                    record[key] = value
                elif key == "post_payload" and isinstance(value, dict):
                    payload = dict(record.get("post_payload") or {})
                    for p_key, p_value in value.items():
                        if p_key in allowed_payload_fields:
                            payload[p_key] = p_value
                    record["post_payload"] = payload

            updated = record
            next_rows.append(record)

        return next_rows, updated

    return _post_store.update(_mutator)


def update_scheduled_campaign(*, scheduled_campaign_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Apply simple metadata updates to a scheduled campaign.

    This is intentionally minimal and currently supports fields like
    strategy_summary and status.
    """

    allowed_fields = {"strategy_summary", "status"}

    def _mutator(rows: list[Dict[str, Any]]) -> tuple[list[Dict[str, Any]], Optional[Dict[str, Any]]]:
        current = list(rows or [])
        updated: Optional[Dict[str, Any]] = None
        next_rows: list[Dict[str, Any]] = []

        for existing in current:
            if existing.get("scheduled_campaign_id") != scheduled_campaign_id:
                next_rows.append(existing)
                continue

            record = dict(existing)
            for key, value in updates.items():
                if key in allowed_fields:
                    record[key] = value
            updated = record
            next_rows.append(record)

        return next_rows, updated

    return _campaign_store.update(_mutator)


def delete_scheduled_post(*, scheduled_post_id: str) -> bool:
    """Remove a scheduled post from storage.

    Returns True if a record was removed, False otherwise.
    """

    def _mutator(rows: list[Dict[str, Any]]) -> tuple[list[Dict[str, Any]], bool]:
        current = list(rows or [])
        next_rows: list[Dict[str, Any]] = []
        removed = False
        for existing in current:
            if existing.get("scheduled_post_id") == scheduled_post_id:
                removed = True
                continue
            next_rows.append(existing)
        return next_rows, removed

    return _post_store.update(_mutator)


def delete_scheduled_campaign(*, scheduled_campaign_id: str) -> bool:
    """Remove a scheduled campaign and all of its posts.

    Returns True if any campaign or posts were removed.
    """

    def _campaign_mutator(rows: list[Dict[str, Any]]) -> tuple[list[Dict[str, Any]], bool]:
        current = list(rows or [])
        next_rows: list[Dict[str, Any]] = []
        removed = False
        for existing in current:
            if existing.get("scheduled_campaign_id") == scheduled_campaign_id:
                removed = True
                continue
            next_rows.append(existing)
        return next_rows, removed

    def _post_mutator(rows: list[Dict[str, Any]]) -> tuple[list[Dict[str, Any]], bool]:
        current = list(rows or [])
        next_rows: list[Dict[str, Any]] = []
        removed = False
        for existing in current:
            if existing.get("scheduled_campaign_id") == scheduled_campaign_id:
                removed = True
                continue
            next_rows.append(existing)
        return next_rows, removed

    removed_campaign = _campaign_store.update(_campaign_mutator)
    removed_posts = _post_store.update(_post_mutator)
    return bool(removed_campaign or removed_posts)
