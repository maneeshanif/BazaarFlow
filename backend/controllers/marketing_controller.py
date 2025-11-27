"""REST endpoints for marketing automation workflows."""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field, field_validator

from ..services.marketing_service import marketing_service
from ..src.exceptions import FacebookAPIError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/marketing", tags=["marketing"])


class AccountCreateRequest(BaseModel):
    user_id: str = Field(..., min_length=1)
    page_id: str = Field(..., min_length=1)
    access_token: str = Field(..., min_length=1)
    page_name: Optional[str] = None
    verify: bool = True


class ScheduleRequest(BaseModel):
    # user_id is optional in dev; backend will fall back to a dev user
    user_id: Optional[str] = None
    times: list[str] = Field(..., min_items=1, max_items=3)
    timezone_name: str = Field(default="UTC", min_length=1)


class ManualCampaignRequest(BaseModel):
    # user_id is optional in dev; backend will fall back to a dev user
    user_id: Optional[str] = None
    prompt: Optional[str] = None
    overrides: Dict[str, Any] = Field(default_factory=dict)

    @field_validator("overrides", mode="before")
    @classmethod
    def _normalise_overrides(cls, value: Any) -> Dict[str, Any]:
        if value is None or value == "" or value == {}:
            return {}
        if isinstance(value, dict):
            return value
        if isinstance(value, str):
            text = value.strip()
            if not text:
                return {}
            try:
                parsed = json.loads(text)
            except json.JSONDecodeError:
                parsed: Dict[str, Any] = {}
                for line in text.replace(";", "\n").splitlines():
                    chunk = line.strip()
                    if not chunk:
                        continue
                    if ":" in chunk:
                        key, raw = chunk.split(":", 1)
                    elif "=" in chunk:
                        key, raw = chunk.split("=", 1)
                    else:
                        raise ValueError(
                            "Overrides must be valid JSON or key:value pairs separated by new lines or semicolons"
                        )
                    parsed[key.strip()] = raw.strip()
            else:
                if not isinstance(parsed, dict):
                    raise ValueError("Overrides JSON must decode to an object")
            return parsed
        raise ValueError("Overrides must be a mapping, JSON string, or key:value text")


class ScheduledTriggerRequest(BaseModel):
    # user_id is optional in dev; backend will fall back to a dev user
    user_id: Optional[str] = None
    triggered_at: Optional[str] = None


class ScheduledPreviewRequest(BaseModel):
    # user_id is optional in dev; backend will fall back to a dev user
    user_id: Optional[str] = None
    prompt: Optional[str] = None
    post_count: int = Field(default=3, ge=1, le=6)
    overrides: Dict[str, Any] = Field(default_factory=dict)

    _normalise_overrides = ManualCampaignRequest._normalise_overrides


class ScheduledCreateRequest(BaseModel):
    # user_id is optional in dev; backend will fall back to a dev user
    user_id: Optional[str] = None
    prompt: Optional[str] = None
    overrides: Dict[str, Any] = Field(default_factory=dict)
    posts: list[Dict[str, Any]] = Field(
        ...,
        min_items=1,
        max_items=6,
        description="List of posts with post_payload and scheduled_at fields",
    )

    _normalise_overrides = ManualCampaignRequest._normalise_overrides


class ScheduledPostUpdateRequest(BaseModel):
    message: Optional[str] = None
    hashtags: Optional[list[str]] = None
    call_to_action: Optional[str] = None
    image_url: Optional[str] = None
    product_sku: Optional[str] = None
    scheduled_at: Optional[str] = Field(
        default=None,
        description="New scheduled_at time as ISO 8601 (UTC preferred)",
    )


class ScheduledCampaignUpdateRequest(BaseModel):
    strategy_summary: Optional[str] = None
    status: Optional[str] = None


class CommentReplyPayload(BaseModel):
    commenter_name: Optional[str] = None
    comment_message: Optional[str] = None


@router.get("/accounts")
async def list_accounts(user_id: Optional[str] = Query(default=None, description="Filter by owner identifier")):
    accounts = marketing_service.get_accounts(user_id=user_id)
    return {"ok": True, "accounts": accounts}


@router.post("/accounts", status_code=201)
async def create_account(payload: AccountCreateRequest):
    try:
        account = marketing_service.register_account(
            user_id=payload.user_id,
            page_id=payload.page_id,
            access_token=payload.access_token,
            page_name=payload.page_name,
            verify=payload.verify,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover - defensive guard
        logger.exception("Failed to register marketing account")
        raise HTTPException(status_code=500, detail="Unable to register marketing account") from exc

    return {"ok": True, "account": account}


@router.delete("/accounts/{account_id}")
async def delete_account(account_id: str):
    removed = marketing_service.remove_account(account_id)
    if not removed:
        raise HTTPException(status_code=404, detail="Account not found")
    return {"ok": True}


@router.put("/accounts/{account_id}/schedule")
async def put_schedule(account_id: str, payload: ScheduleRequest):
    try:
        schedule = marketing_service.configure_schedule(
            account_id=account_id,
            user_id=payload.user_id,
            times=payload.times,
            timezone_name=payload.timezone_name,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"ok": True, "schedule": schedule}


@router.get("/accounts/{account_id}/schedule")
async def get_schedule(account_id: str):
    schedule = marketing_service.fetch_schedule(account_id)
    if not schedule:
        return {
            "ok": True,
            "schedule": {
                "account_id": account_id,
                "user_id": None,
                "times": [],
                "timezone": "UTC",
                "last_triggered_at": None,
                "configured": False,
            },
        }
    return {"ok": True, "schedule": {**schedule, "configured": True}}


@router.post("/accounts/{account_id}/campaign")
async def trigger_manual_campaign(account_id: str, payload: ManualCampaignRequest):
    try:
        result = await marketing_service.trigger_manual_campaign(
            account_id=account_id,
            user_id=payload.user_id,
            prompt=payload.prompt,
            overrides=payload.overrides,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover - defensive guard
        logger.exception("Manual campaign execution failed")
        raise HTTPException(status_code=500, detail="Failed to execute marketing campaign") from exc

    return {"ok": True, "result": result}


@router.post("/accounts/{account_id}/campaign/scheduled")
async def trigger_scheduled_campaign(account_id: str, payload: ScheduledTriggerRequest):
    try:
        result = await marketing_service.trigger_scheduled_campaign(
            account_id=account_id,
            user_id=payload.user_id,
            triggered_at=payload.triggered_at,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover - defensive guard
        logger.exception("Scheduled campaign execution failed")
        raise HTTPException(status_code=500, detail="Failed to execute scheduled marketing campaign") from exc

    return {"ok": True, "result": result}


@router.post("/accounts/{account_id}/scheduled/preview")
async def preview_scheduled_campaign(account_id: str, payload: ScheduledPreviewRequest):
    """Generate a campaign preview for scheduling without publishing.

    This endpoint runs the marketing agent with mode="scheduled" and returns
    the structured campaign payload (including posts) without posting to
    Facebook or recording posts.
    """

    try:
        # Ensure post_count hint is visible to the agent via overrides.
        overrides = dict(payload.overrides)
        overrides.setdefault("post_count", payload.post_count)
        account = marketing_service._require_account(account_id)  # type: ignore[attr-defined]
        campaign = await marketing_service._generate_campaign(  # type: ignore[attr-defined]
            account=account,
            user_id=payload.user_id,
            mode="scheduled",
            prompt=payload.prompt,
            overrides=overrides,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover - defensive guard
        logger.exception("Scheduled campaign preview failed")
        raise HTTPException(status_code=500, detail="Failed to generate scheduled campaign preview") from exc

    return {"ok": True, "campaign": campaign}


@router.post("/accounts/{account_id}/scheduled")
async def create_scheduled_campaign(account_id: str, payload: ScheduledCreateRequest):
    """Persist a scheduled campaign made up of generated posts.

    The posts field should contain objects with at least:
    - post_payload: CampaignPost-like dict
    - scheduled_at: ISO 8601 timestamp (ideally in UTC)
    """

    posts_with_times: list[Dict[str, Any]] = []
    for index, item in enumerate(payload.posts):
        if not isinstance(item, dict):
            raise HTTPException(status_code=400, detail=f"Post at index {index} must be an object")
        post_payload = item.get("post_payload") or item.get("payload") or item
        scheduled_at = item.get("scheduled_at")
        if not scheduled_at:
            raise HTTPException(status_code=400, detail=f"scheduled_at is required for post index {index}")
        posts_with_times.append({"post_payload": post_payload, "scheduled_at": scheduled_at})

    try:
        result = await marketing_service.create_scheduled_campaign(
            account_id=account_id,
            user_id=payload.user_id,
            prompt=payload.prompt,
            overrides=payload.overrides,
            posts_with_times=posts_with_times,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover - defensive guard
        logger.exception("Failed to create scheduled campaign")
        raise HTTPException(status_code=500, detail="Failed to create scheduled campaign") from exc

    return {"ok": True, **result}


@router.get("/accounts/{account_id}/posts")
async def list_posts(account_id: str, limit: int = Query(default=20, ge=1, le=100)):
    posts = marketing_service.get_recent_posts(account_id, limit=limit)
    return {"ok": True, "posts": posts}


@router.get("/accounts/{account_id}/scheduled/activity")
async def get_scheduled_activity(account_id: str):
    """Return scheduled posts for the activity dashboard.

    The payload exposes raw scheduled post records so the frontend can
    group and render them alongside recently published campaigns.
    """

    payload = marketing_service.list_scheduled_activity(account_id)
    return {"ok": True, **payload}


@router.post("/accounts/{account_id}/posts/{facebook_post_id}/insights")
async def refresh_post_insights(account_id: str, facebook_post_id: str):
    try:
        updated = marketing_service.refresh_post_insights(account_id=account_id, facebook_post_id=facebook_post_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover - defensive guard
        logger.exception("Failed to refresh marketing post insights")
        raise HTTPException(status_code=500, detail="Could not refresh insights") from exc

    if not updated:
        raise HTTPException(status_code=404, detail="Post not found")
    return {"ok": True, "post": updated}


@router.patch("/accounts/{account_id}/scheduled/posts/{scheduled_post_id}")
async def patch_scheduled_post(account_id: str, scheduled_post_id: str, payload: ScheduledPostUpdateRequest):
    """Update a pending scheduled post's content or scheduled time.

    For now we trust account_id as a routing component and do not cross-check
    it against the stored record, but this can be tightened later if needed.
    """

    try:
        post_payload: Dict[str, Any] = {}
        if payload.message is not None:
            post_payload["message"] = payload.message
        if payload.hashtags is not None:
            post_payload["hashtags"] = payload.hashtags
        if payload.call_to_action is not None:
            post_payload["call_to_action"] = payload.call_to_action
        if payload.image_url is not None:
            post_payload["image_url"] = payload.image_url
        if payload.product_sku is not None:
            post_payload["product_sku"] = payload.product_sku

        updated = marketing_service.update_scheduled_post(
            scheduled_post_id=scheduled_post_id,
            post_payload=post_payload or None,
            scheduled_at=payload.scheduled_at,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {"ok": True, "post": updated}


@router.patch("/accounts/{account_id}/scheduled/campaigns/{scheduled_campaign_id}")
async def patch_scheduled_campaign(
    account_id: str,
    scheduled_campaign_id: str,
    payload: ScheduledCampaignUpdateRequest,
):
    """Update simple metadata for a scheduled campaign (e.g. strategy summary)."""

    try:
        updated = marketing_service.update_scheduled_campaign(
            scheduled_campaign_id=scheduled_campaign_id,
            strategy_summary=payload.strategy_summary,
            status=payload.status,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {"ok": True, "campaign": updated}


@router.delete("/accounts/{account_id}/scheduled/posts/{scheduled_post_id}")
async def delete_scheduled_post(account_id: str, scheduled_post_id: str):
    """Remove a pending scheduled post from the queue."""

    try:
        marketing_service.delete_scheduled_post(scheduled_post_id=scheduled_post_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {"ok": True}


@router.delete("/accounts/{account_id}/scheduled/campaigns/{scheduled_campaign_id}")
async def delete_scheduled_campaign(account_id: str, scheduled_campaign_id: str):
    """Remove a scheduled campaign and all of its scheduled posts."""

    try:
        marketing_service.delete_scheduled_campaign(scheduled_campaign_id=scheduled_campaign_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {"ok": True}


@router.get("/accounts/{account_id}/posts/{facebook_post_id}/comments")
async def get_post_comments(account_id: str, facebook_post_id: str, limit: int = Query(default=50, ge=1, le=100)):
    try:
        payload = marketing_service.get_post_comments(
            account_id=account_id,
            facebook_post_id=facebook_post_id,
            limit=limit,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except FacebookAPIError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return {
        "ok": True,
        "comments": payload.get("comments", []),
        "total_count": payload.get("total_count", 0),
        "has_next_page": payload.get("has_next_page", False),
        "next_cursor": payload.get("next_cursor"),
        "keywords": payload.get("keywords"),
        "fetched_at": payload.get("fetched_at"),
    }


@router.delete("/accounts/{account_id}/posts/{facebook_post_id}")
async def delete_post(account_id: str, facebook_post_id: str, remove_remote: bool = Query(default=True)):
    try:
        result = marketing_service.delete_post(
            account_id=account_id,
            facebook_post_id=facebook_post_id,
            remove_remote=remove_remote,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except FacebookAPIError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    removed_remote = result.get("removed_remote")
    removed_local = result.get("removed_local", False)

    if remove_remote and removed_remote is False:
        raise HTTPException(status_code=404, detail="Facebook post not found")
    if not removed_local:
        raise HTTPException(status_code=404, detail="Post not found in BazaarFlow records")

    return {"ok": True, "removed_remote": removed_remote, "removed_local": removed_local}


@router.post("/accounts/{account_id}/posts/{facebook_post_id}/comments/{comment_id}/reply")
async def reply_to_comment(
    account_id: str,
    facebook_post_id: str,
    comment_id: str,
    payload: CommentReplyPayload,
):
    try:
        result = marketing_service.reply_to_comment(
            account_id=account_id,
            facebook_post_id=facebook_post_id,
            comment_id=comment_id,
            comment_message=payload.comment_message,
            commenter_name=payload.commenter_name,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except FacebookAPIError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return {"ok": True, **result}
