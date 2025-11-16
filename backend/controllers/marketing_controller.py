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
    user_id: str = Field(..., min_length=1)
    times: list[str] = Field(..., min_items=1, max_items=3)
    timezone_name: str = Field(default="UTC", min_length=1)


class ManualCampaignRequest(BaseModel):
    user_id: str = Field(..., min_length=1)
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
    user_id: str = Field(..., min_length=1)
    triggered_at: Optional[str] = None


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
        raise HTTPException(status_code=404, detail="Schedule not configured")
    return {"ok": True, "schedule": schedule}


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


@router.get("/accounts/{account_id}/posts")
async def list_posts(account_id: str, limit: int = Query(default=20, ge=1, le=100)):
    posts = marketing_service.get_recent_posts(account_id, limit=limit)
    return {"ok": True, "posts": posts}


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
