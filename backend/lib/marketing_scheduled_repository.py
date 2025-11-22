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


_campaign_store = JsonStore(_SCHEDULED_CAMPAIGNS_PATH, key_field="scheduled_campaign_id")
_post_store = JsonStore(_SCHEDULED_POSTS_PATH, key_field="scheduled_post_id")


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
    _campaign_store.upsert(asdict(campaign))

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
        _post_store.upsert(asdict(record))
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

    results: List[Dict[str, Any]] = []
    for record in _post_store.iter_rows():
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
    record = _post_store.get(scheduled_post_id)
    if not record:
        return None
    record["status"] = "posted"
    record["facebook_post_id"] = facebook_post_id
    record["error"] = None
    _post_store.upsert(record)
    return record


def mark_scheduled_post_failed(*, scheduled_post_id: str, error: str) -> Optional[Dict[str, Any]]:
    record = _post_store.get(scheduled_post_id)
    if not record:
        return None
    record["status"] = "failed"
    record["error"] = error
    _post_store.upsert(record)
    return record


def get_scheduled_post(*, scheduled_post_id: str) -> Optional[Dict[str, Any]]:
    return _post_store.get(scheduled_post_id)
