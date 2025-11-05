"""
Facebook Manager Tool
A type-safe Python tool for managing Facebook page posts and interactions.
"""

from .facebook_manager import FacebookManager
from .config import FacebookConfig, get_config, load_config
from .models import (
    TextPostRequest,
    ImagePostRequest,
    VideoPostRequest,
    FacebookPostResponse,
    FacebookErrorResponse,
    PostType,
    PageInfo,
    PostMetrics,
    # Comment models
    CommentData,
    CommentsResponse,
    CommentReplyRequest,
    CommentReactionRequest,
    CommentActionResponse,
    ReactionType,
    # Insights models
    PostInsights,
    PageInsights,
    ReactionBreakdown,
    InsightPeriod,
)
from .exceptions import (
    FacebookManagerError,
    FacebookAPIError,
    InvalidCredentialsError,
    PostCreationError,
    ImageUploadError,
    VideoUploadError,
    ConfigurationError
)

__version__ = "0.1.0"

__all__ = [
    # Main classes
    "FacebookManager",
    
    # Configuration
    "FacebookConfig",
    "get_config",
    "load_config",
    
    # Post Models
    "TextPostRequest",
    "ImagePostRequest",
    "VideoPostRequest",
    "FacebookPostResponse",
    "FacebookErrorResponse",
    "PostType",
    "PageInfo",
    "PostMetrics",
    
    # Comment Models
    "CommentData",
    "CommentsResponse",
    "CommentReplyRequest",
    "CommentReactionRequest",
    "CommentActionResponse",
    "ReactionType",
    
    # Insights Models
    "PostInsights",
    "PageInsights",
    "ReactionBreakdown",
    "InsightPeriod",
    
    # Exceptions
    "FacebookManagerError",
    "FacebookAPIError",
    "InvalidCredentialsError",
    "PostCreationError",
    "ImageUploadError",
    "VideoUploadError",
    "ConfigurationError",
]
