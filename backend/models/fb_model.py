"""Pydantic models used by the Facebook Manager integration."""

from __future__ import annotations

from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field, HttpUrl, field_validator, model_validator


class PostType(str, Enum):
    """Supported post types for the Facebook page."""

    TEXT = "TEXT"
    IMAGE = "IMAGE"
    VIDEO = "VIDEO"


class ReactionType(str, Enum):
    """Available reaction types for comment interactions."""

    LIKE = "LIKE"
    LOVE = "LOVE"
    WOW = "WOW"
    HAHA = "HAHA"
    SAD = "SAD"
    ANGRY = "ANGRY"
    CARE = "CARE"


class InsightPeriod(str, Enum):
    """Insight aggregation windows supported by the Graph API."""

    LAST_24_HOURS = "day"
    LAST_7_DAYS = "week"
    LAST_28_DAYS = "days_28"
    LIFETIME = "lifetime"


class TextPostRequest(BaseModel):
    """Payload for publishing a text-only post."""

    message: str = Field(..., min_length=1, max_length=63206)

    @field_validator("message")
    @classmethod
    def validate_message(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Message cannot be empty or whitespace")
        if len(cleaned) > 63206:
            raise ValueError("Message exceeds Facebook's maximum length (63206 characters)")
        return cleaned


class ImagePostRequest(BaseModel):
    """Payload for publishing an image post."""

    message: Optional[str] = Field(default=None, max_length=2200)
    image_url: Optional[HttpUrl] = None
    image_path: Optional[str] = None
    published: bool = True

    @model_validator(mode="after")
    def validate_image_source(self) -> "ImagePostRequest":
        has_url = bool(self.image_url)
        has_path = bool(self.image_path)
        if has_url == has_path:
            raise ValueError("Provide exactly one of image_url or image_path")
        return self

    @field_validator("message")
    @classmethod
    def validate_message(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        cleaned = value.strip()
        if not cleaned:
            return None
        return cleaned


class VideoPostRequest(BaseModel):
    """Payload for publishing a video post."""

    description: Optional[str] = Field(default=None, max_length=2200)
    video_url: Optional[HttpUrl] = None
    video_path: Optional[str] = None
    thumb_image_url: Optional[HttpUrl] = None
    published: bool = True

    @model_validator(mode="after")
    def validate_video_source(self) -> "VideoPostRequest":
        has_url = bool(self.video_url)
        has_path = bool(self.video_path)
        if has_url == has_path:
            raise ValueError("Provide exactly one of video_url or video_path")
        return self


class FacebookPostResponse(BaseModel):
    """Standard response returned after publishing content."""

    post_id: str
    success: bool = True
    message: Optional[str] = None
    raw_response: Optional[Dict[str, object]] = None


class FacebookErrorResponse(BaseModel):
    """Shape of error payloads returned by the Graph API."""

    error_code: int
    error_message: str
    error_type: str
    error_subcode: Optional[int] = None


class CommentData(BaseModel):
    """Represents a single comment on a post."""

    comment_id: str
    post_id: str
    message: str = ""
    from_user: Dict[str, str] = Field(default_factory=dict)
    created_time: str = ""
    like_count: int = 0
    comment_count: int = 0
    is_hidden: bool = False
    parent_comment_id: Optional[str] = None
    attachment: Optional[Dict[str, object]] = None


class CommentsResponse(BaseModel):
    """Container for paginated comments and any extracted keywords."""

    comments: List[CommentData] = Field(default_factory=list)
    total_count: int = 0
    has_next_page: bool = False
    next_cursor: Optional[str] = None
    keywords: Optional[List[Dict[str, object]]] = None


class CommentReplyRequest(BaseModel):
    """Payload for replying to a comment."""

    comment_id: str
    message: str = Field(..., min_length=1, max_length=8000)

    @field_validator("message")
    @classmethod
    def validate_message(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Reply message cannot be empty")
        return cleaned


class CommentReactionRequest(BaseModel):
    """Payload for reacting to a comment."""

    comment_id: str
    reaction_type: ReactionType = ReactionType.LIKE


class CommentActionResponse(BaseModel):
    """Response returned after performing an action on a comment."""

    success: bool
    comment_id: Optional[str] = None
    action: Optional[str] = None
    message: str = "Action completed successfully"
    is_hidden: Optional[bool] = None


class ReactionBreakdown(BaseModel):
    """Aggregated reaction counts for a post."""

    like: int = 0
    love: int = 0
    wow: int = 0
    haha: int = 0
    sad: int = 0
    angry: int = 0
    care: int = 0

    @property
    def total(self) -> int:
        return self.like + self.love + self.wow + self.haha + self.sad + self.angry + self.care

    @property
    def computed_total(self) -> int:  # Backwards compatibility with docs wording
        return self.total


class PostInsights(BaseModel):
    """Metrics describing how a specific post performed."""

    post_id: str
    period: InsightPeriod
    reach: int = 0
    impressions: int = 0
    reactions: ReactionBreakdown = Field(default_factory=ReactionBreakdown)
    comments_count: int = 0
    shares_count: int = 0
    clicked: int = 0
    engagement_rate: float = 0.0

    @property
    def computed_engagement_rate(self) -> float:
        if self.reach <= 0:
            return 0.0
        engagement = self.reactions.total + self.comments_count + self.shares_count + self.clicked
        return round((engagement / self.reach) * 100, 2)


class PageInsights(BaseModel):
    """Metrics describing overall Facebook page performance."""

    page_id: str
    period: InsightPeriod
    page_impressions: int = 0
    page_reach: int = 0
    page_engaged_users: int = 0
    page_post_engagements: int = 0
    page_fans: int = 0
    page_fans_online: int = 0
    page_views_total: int = 0
    page_consumptions: int = 0


__all__ = [
    "CommentActionResponse",
    "CommentData",
    "CommentReactionRequest",
    "CommentReplyRequest",
    "CommentsResponse",
    "FacebookErrorResponse",
    "FacebookPostResponse",
    "ImagePostRequest",
    "InsightPeriod",
    "PageInsights",
    "PostInsights",
    "PostType",
    "ReactionBreakdown",
    "ReactionType",
    "TextPostRequest",
    "VideoPostRequest",
]