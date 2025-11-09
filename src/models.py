"""
Pydantic models for Facebook Manager Tool
Provides type-safe data structures for Facebook API interactions
"""

from typing import Optional, Literal, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, HttpUrl, field_validator, ConfigDict
from enum import Enum


class PostType(str, Enum):
    """Enumeration of supported Facebook post types"""
    TEXT = "text"
    TEXT_WITH_IMAGE = "text_with_image"
    IMAGE = "image"
    VIDEO = "video"
    VIDEO_WITH_TEXT = "video_with_text"


class TextPostRequest(BaseModel):
    """Request model for creating a text-only post"""
    message: str = Field(
        ..., 
        min_length=1, 
        max_length=63206,
        description="The text content of the post"
    )
    
    @field_validator('message')
    @classmethod
    def validate_message(cls, v: str) -> str:
        """Ensure message is not just whitespace"""
        if not v.strip():
            raise ValueError("Message cannot be empty or only whitespace")
        return v.strip()


class ImagePostRequest(BaseModel):
    """Request model for creating a post with image"""
    message: Optional[str] = Field(
        None,
        max_length=63206,
        description="Optional text content to accompany the image"
    )
    image_url: Optional[HttpUrl] = Field(
        None,
        description="URL of the image to post (for URL-based uploads)"
    )
    image_path: Optional[str] = Field(
        None,
        description="Local file path to the image (for file-based uploads)"
    )
    
    @field_validator('message')
    @classmethod
    def validate_message(cls, v: Optional[str]) -> Optional[str]:
        """Trim whitespace from message if provided"""
        if v is not None:
            return v.strip() if v.strip() else None
        return v
    
    def model_post_init(self, __context) -> None:
        """Validate that either image_url or image_path is provided"""
        if not self.image_url and not self.image_path:
            raise ValueError("Either image_url or image_path must be provided")
        if self.image_url and self.image_path:
            raise ValueError("Only one of image_url or image_path should be provided")


class VideoPostRequest(BaseModel):
    """Request model for creating a post with video (future implementation)"""
    message: Optional[str] = Field(
        None,
        max_length=63206,
        description="Optional text content to accompany the video"
    )
    video_url: Optional[HttpUrl] = Field(
        None,
        description="URL of the video to post"
    )
    video_path: Optional[str] = Field(
        None,
        description="Local file path to the video"
    )
    
    def model_post_init(self, __context) -> None:
        """Validate that either video_url or video_path is provided"""
        if not self.video_url and not self.video_path:
            raise ValueError("Either video_url or video_path must be provided")


class FacebookPostResponse(BaseModel):
    """Response model for Facebook post creation"""
    post_id: str = Field(..., description="The ID of the created post")
    success: bool = Field(default=True, description="Whether the post was successful")
    message: Optional[str] = Field(None, description="Additional information about the post")


class FacebookErrorResponse(BaseModel):
    """Error response model from Facebook API"""
    error_code: int = Field(..., description="Facebook error code")
    error_message: str = Field(..., description="Error message from Facebook")
    error_type: str = Field(..., description="Type of error")
    error_subcode: Optional[int] = Field(None, description="Error subcode if available")


class PageInfo(BaseModel):
    """Model for Facebook page information"""
    page_id: str = Field(..., description="Facebook page ID")
    page_name: Optional[str] = Field(None, description="Name of the page")
    access_token: str = Field(..., description="Page access token")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "page_id": "123456789",
                "page_name": "My Facebook Page",
                "access_token": "EAAxxxxx"
            }
        }
    )


class PostMetrics(BaseModel):
    """Model for post engagement metrics (for monitoring)"""
    post_id: str
    likes: int = 0
    comments: int = 0
    shares: int = 0
    reactions: dict = Field(default_factory=dict)
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "post_id": "123456789_987654321",
                "likes": 42,
                "comments": 5,
                "shares": 3,
                "reactions": {"LIKE": 30, "LOVE": 10, "WOW": 2}
            }
        }
    )


# ============================================================================
# COMMENT MODELS
# ============================================================================

class ReactionType(str, Enum):
    """Facebook reaction types"""
    LIKE = "LIKE"
    LOVE = "LOVE"
    WOW = "WOW"
    HAHA = "HAHA"
    SAD = "SAD"
    ANGRY = "ANGRY"
    CARE = "CARE"


class CommentData(BaseModel):
    """Model for a Facebook comment"""
    comment_id: str = Field(..., description="Comment ID")
    post_id: str = Field(..., description="Parent post ID")
    message: str = Field(..., description="Comment text")
    from_user: Dict[str, str] = Field(..., description="User who made the comment")
    created_time: str = Field(..., description="When the comment was created")
    like_count: int = Field(default=0, description="Number of likes on comment")
    comment_count: int = Field(default=0, description="Number of replies to comment")
    is_hidden: bool = Field(default=False, description="Whether comment is hidden")
    parent_comment_id: Optional[str] = Field(None, description="Parent comment ID if this is a reply")
    attachment: Optional[Dict[str, Any]] = Field(None, description="Comment attachment data")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "comment_id": "123456789_987654321",
                "post_id": "123456789_111111111",
                "message": "Great post!",
                "from_user": {"name": "John Doe", "id": "987654321"},
                "created_time": "2025-11-03T15:25:16+0000",
                "like_count": 5,
                "comment_count": 2
            }
        }
    )


class CommentsResponse(BaseModel):
    """Response model for comments retrieval"""
    comments: List[CommentData] = Field(default_factory=list, description="List of comments")
    total_count: int = Field(..., description="Total number of comments")
    has_next_page: bool = Field(default=False, description="Whether more comments are available")
    next_cursor: Optional[str] = Field(None, description="Cursor for pagination")
    keywords: List[Dict[str, Any]] = Field(default_factory=list, description="Extracted keywords with frequency")


class CommentReplyRequest(BaseModel):
    """Request model for replying to a comment"""
    comment_id: str = Field(..., description="ID of the comment to reply to")
    message: str = Field(..., min_length=1, max_length=8000, description="Reply message")
    
    @field_validator('message')
    @classmethod
    def validate_message(cls, v: str) -> str:
        """Ensure message is not just whitespace"""
        if not v.strip():
            raise ValueError("Reply message cannot be empty or only whitespace")
        return v.strip()


class CommentReactionRequest(BaseModel):
    """Request model for reacting to a comment"""
    comment_id: str = Field(..., description="ID of the comment to react to")
    reaction_type: ReactionType = Field(default=ReactionType.LIKE, description="Type of reaction")


class CommentActionResponse(BaseModel):
    """Response model for comment actions"""
    success: bool = Field(..., description="Whether the action was successful")
    comment_id: str = Field(..., description="Comment ID")
    action: str = Field(..., description="Action performed")
    message: Optional[str] = Field(None, description="Additional information")


# ============================================================================
# INSIGHTS MODELS
# ============================================================================

class InsightPeriod(str, Enum):
    """Time period for insights aligned with Graph API periods"""
    LAST_24_HOURS = "day"
    LAST_7_DAYS = "week"
    LAST_28_DAYS = "days_28"
    LIFETIME = "lifetime"


class ReactionBreakdown(BaseModel):
    """Breakdown of reactions by type"""
    like: int = Field(default=0, description="Number of likes")
    love: int = Field(default=0, description="Number of love reactions")
    wow: int = Field(default=0, description="Number of wow reactions")
    haha: int = Field(default=0, description="Number of haha reactions")
    sad: int = Field(default=0, description="Number of sad reactions")
    angry: int = Field(default=0, description="Number of angry reactions")
    care: int = Field(default=0, description="Number of care reactions")
    total: int = Field(default=0, description="Total reactions")
    
    @property
    def computed_total(self) -> int:
        """Calculate total reactions"""
        return self.like + self.love + self.wow + self.haha + self.sad + self.angry + self.care
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "like": 100,
                "love": 50,
                "wow": 10,
                "haha": 5,
                "sad": 2,
                "angry": 1,
                "care": 3,
                "total": 171
            }
        }
    )


class PostInsights(BaseModel):
    """Model for post insights/analytics"""
    post_id: str = Field(..., description="Post ID")
    period: InsightPeriod = Field(..., description="Time period for insights")
    reach: int = Field(default=0, description="Number of unique users who saw the post")
    impressions: int = Field(default=0, description="Total number of times post was displayed")
    reactions: ReactionBreakdown = Field(default_factory=ReactionBreakdown, description="Breakdown of reactions")
    comments_count: int = Field(default=0, description="Number of comments")
    shares_count: int = Field(default=0, description="Number of shares")
    engagement_rate: float = Field(default=0.0, description="Engagement rate percentage")
    clicked: int = Field(default=0, description="Number of clicks on the post")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "post_id": "123456789_987654321",
                "period": "day",
                "reach": 1000,
                "impressions": 1500,
                "reactions": {
                    "like": 100,
                    "love": 50,
                    "total": 150
                },
                "comments_count": 25,
                "shares_count": 10,
                "engagement_rate": 18.5
            }
        }
    )


class PageInsights(BaseModel):
    """Model for page-level insights"""
    page_id: str = Field(..., description="Page ID")
    period: InsightPeriod = Field(..., description="Time period for insights")
    page_impressions: int = Field(default=0, description="Total page impressions")
    page_reach: int = Field(default=0, description="Total page reach")
    page_engaged_users: int = Field(default=0, description="Number of engaged users")
    page_post_engagements: int = Field(default=0, description="Total post engagements")
    page_fans: int = Field(default=0, description="Total page followers/fans")
    page_fans_online: int = Field(default=0, description="Fans online")
    page_views_total: int = Field(default=0, description="Total page views")
    page_consumptions: int = Field(default=0, description="Content consumptions")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "page_id": "123456789",
                "period": "day",
                "page_impressions": 5000,
                "page_reach": 3000,
                "page_engaged_users": 500,
                "page_fans": 10000
            }
        }
    )
