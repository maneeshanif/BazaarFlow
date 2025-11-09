#!/usr/bin/env python3
"""
Facebook Manager MCP Server

A Model Context Protocol server that exposes Facebook Page management capabilities
as standardized tools that can be integrated with any MCP-compatible system.

This server provides tools for:
- Posting content (text, images)
- Fetching and analyzing comments
- Managing comments (reply, hide, delete, like)
- Retrieving post and page insights
- Verifying credentials

For more information about MCP: https://modelcontextprotocol.io/
"""

import asyncio
import json
import logging
import sys
from typing import Any, Dict, List, Optional, Sequence

from dotenv import load_dotenv
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    Tool,
    TextContent,
    ImageContent,
    EmbeddedResource,
    LoggingLevel,
)
from pydantic import BaseModel, Field, ValidationError

# Load environment variables
load_dotenv()

# Import Facebook Manager components
from src import (
    FacebookManager,
    FacebookConfig,
    TextPostRequest,
    ImagePostRequest,
    CommentReplyRequest,
    CommentReactionRequest,
    InsightPeriod,
    load_config,
)
from src.exceptions import (
    FacebookAPIError,
    InvalidCredentialsError,
    PostCreationError,
    ImageUploadError,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("facebook-mcp-server")

# Initialize the MCP server
app = Server("facebook-manager")

# Global config instance
_config: Optional[FacebookConfig] = None


def get_config() -> FacebookConfig:
    """Get or initialize the Facebook configuration."""
    global _config
    if _config is None:
        try:
            _config = load_config()
            logger.info(f"Configuration loaded for page: {_config.facebook_page_id}")
        except ValidationError as e:
            logger.error(f"Configuration validation failed: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to load configuration: {e}")
            raise
    return _config


# =============================================================================
# Tool Definitions
# =============================================================================

TOOLS: List[Tool] = [
    Tool(
        name="verify_facebook_credentials",
        description=(
            "Verify that the configured Facebook Page credentials are valid and working. "
            "This checks if the access token is valid and has necessary permissions. "
            "Use this before other operations to ensure connectivity."
        ),
        inputSchema={
            "type": "object",
            "properties": {},
            "required": [],
        },
    ),
    Tool(
        name="post_text_to_facebook",
        description=(
            "Publish a text-only post to the configured Facebook Page. "
            "The post will be immediately visible to your page followers."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "message": {
                    "type": "string",
                    "description": "The text content to post (1-63206 characters)",
                    "minLength": 1,
                    "maxLength": 63206,
                }
            },
            "required": ["message"],
        },
    ),
    Tool(
        name="post_image_to_facebook",
        description=(
            "Publish an image post to the configured Facebook Page. "
            "You can provide either a public image URL or a local file path. "
            "Optionally include a text caption."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "image_url": {
                    "type": "string",
                    "description": "Public URL of the image to post (JPEG, PNG, GIF)",
                },
                "image_path": {
                    "type": "string",
                    "description": "Local filesystem path to the image file",
                },
                "message": {
                    "type": "string",
                    "description": "Optional caption/message to accompany the image",
                },
            },
            "oneOf": [
                {"required": ["image_url"]},
                {"required": ["image_path"]},
            ],
        },
    ),
    Tool(
        name="fetch_post_comments",
        description=(
            "Retrieve comments from a specific Facebook post. "
            "Returns comment text, author info, timestamps, like counts, and reply counts. "
            "Optionally extracts trending keywords from the comments."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "post_id": {
                    "type": "string",
                    "description": "The Facebook post ID (format: PageID_PostID)",
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of comments to retrieve",
                    "default": 100,
                    "minimum": 1,
                    "maximum": 500,
                },
                "extract_keywords": {
                    "type": "boolean",
                    "description": "Whether to extract and return trending keywords",
                    "default": True,
                },
            },
            "required": ["post_id"],
        },
    ),
    Tool(
        name="fetch_post_insights",
        description=(
            "Retrieve engagement metrics and insights for a specific Facebook post. "
            "Returns reach, impressions, reactions breakdown, comments count, shares, "
            "clicks, and engagement rate. Supports multiple time periods."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "post_id": {
                    "type": "string",
                    "description": "The Facebook post ID (format: PageID_PostID)",
                },
                "period": {
                    "type": "string",
                    "description": "Time period for insights",
                    "enum": ["day", "week", "days_28", "lifetime"],
                    "default": "lifetime",
                },
            },
            "required": ["post_id"],
        },
    ),
    Tool(
        name="fetch_page_insights",
        description=(
            "Retrieve page-level engagement metrics for the configured Facebook Page. "
            "Returns impressions, reach, engaged users, post engagements, fan count, "
            "page views, and content consumptions for the specified period."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "period": {
                    "type": "string",
                    "description": "Time period for insights",
                    "enum": ["day", "week", "days_28"],
                    "default": "day",
                },
            },
            "required": [],
        },
    ),
    Tool(
        name="reply_to_comment",
        description=(
            "Reply to a specific comment on your Facebook Page. "
            "The reply will be posted as the page, not as a personal profile."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "comment_id": {
                    "type": "string",
                    "description": "The Facebook comment ID to reply to",
                },
                "message": {
                    "type": "string",
                    "description": "Your reply message (1-8000 characters)",
                    "minLength": 1,
                    "maxLength": 8000,
                },
            },
            "required": ["comment_id", "message"],
        },
    ),
    Tool(
        name="like_comment",
        description=(
            "Like a comment on your Facebook Page as the page. "
            "This shows engagement with your community."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "comment_id": {
                    "type": "string",
                    "description": "The Facebook comment ID to like",
                },
            },
            "required": ["comment_id"],
        },
    ),
    Tool(
        name="hide_comment",
        description=(
            "Hide a specific comment from public view on your Facebook Page. "
            "The comment author can still see it, but others cannot. "
            "Useful for moderating inappropriate content."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "comment_id": {
                    "type": "string",
                    "description": "The Facebook comment ID to hide",
                },
            },
            "required": ["comment_id"],
        },
    ),
    Tool(
        name="delete_comment",
        description=(
            "Permanently delete a comment from your Facebook Page. "
            "This action cannot be undone. Use with caution."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "comment_id": {
                    "type": "string",
                    "description": "The Facebook comment ID to delete",
                },
            },
            "required": ["comment_id"],
        },
    ),
    Tool(
        name="extract_comment_keywords",
        description=(
            "Extract and analyze trending keywords from a list of comments. "
            "Useful for understanding what topics your audience is discussing."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "post_id": {
                    "type": "string",
                    "description": "The Facebook post ID to analyze comments from",
                },
                "top_n": {
                    "type": "integer",
                    "description": "Number of top keywords to return",
                    "default": 20,
                    "minimum": 1,
                    "maximum": 100,
                },
                "min_length": {
                    "type": "integer",
                    "description": "Minimum word length to consider as keyword",
                    "default": 3,
                    "minimum": 1,
                },
            },
            "required": ["post_id"],
        },
    ),
]


# =============================================================================
# Tool Handlers
# =============================================================================

async def handle_verify_credentials(arguments: Dict[str, Any]) -> List[TextContent]:
    """Handle credential verification."""
    try:
        config = get_config()
        with FacebookManager(config=config) as manager:
            success = manager.verify_credentials()
            
            if success:
                return [TextContent(
                    type="text",
                    text=json.dumps({
                        "success": True,
                        "message": "Facebook credentials verified successfully",
                        "page_id": config.facebook_page_id,
                        "api_version": config.facebook_api_version,
                    }, indent=2)
                )]
            else:
                return [TextContent(
                    type="text",
                    text=json.dumps({
                        "success": False,
                        "message": "Credential verification failed without error",
                    }, indent=2)
                )]
    
    except InvalidCredentialsError as e:
        return [TextContent(
            type="text",
            text=json.dumps({
                "success": False,
                "error": "Invalid credentials",
                "message": str(e),
            }, indent=2)
        )]
    
    except Exception as e:
        logger.error(f"Credential verification error: {e}")
        return [TextContent(
            type="text",
            text=json.dumps({
                "success": False,
                "error": type(e).__name__,
                "message": str(e),
            }, indent=2)
        )]


async def handle_post_text(arguments: Dict[str, Any]) -> List[TextContent]:
    """Handle text post creation."""
    try:
        message = arguments["message"]
        
        config = get_config()
        request = TextPostRequest(message=message)
        
        with FacebookManager(config=config) as manager:
            response = manager.create_text_post(request)
            
            return [TextContent(
                type="text",
                text=json.dumps({
                    "success": True,
                    "post_id": response.post_id,
                    "message": "Text post published successfully",
                }, indent=2)
            )]
    
    except ValidationError as e:
        return [TextContent(
            type="text",
            text=json.dumps({
                "success": False,
                "error": "Validation error",
                "details": [{"field": err["loc"][0], "message": err["msg"]} for err in e.errors()],
            }, indent=2)
        )]
    
    except PostCreationError as e:
        return [TextContent(
            type="text",
            text=json.dumps({
                "success": False,
                "error": "Post creation failed",
                "message": str(e),
            }, indent=2)
        )]
    
    except Exception as e:
        logger.error(f"Text post error: {e}")
        return [TextContent(
            type="text",
            text=json.dumps({
                "success": False,
                "error": type(e).__name__,
                "message": str(e),
            }, indent=2)
        )]


async def handle_post_image(arguments: Dict[str, Any]) -> List[TextContent]:
    """Handle image post creation."""
    try:
        config = get_config()
        request = ImagePostRequest(
            message=arguments.get("message"),
            image_url=arguments.get("image_url"),
            image_path=arguments.get("image_path"),
        )
        
        with FacebookManager(config=config) as manager:
            response = manager.create_image_post(request)
            
            return [TextContent(
                type="text",
                text=json.dumps({
                    "success": True,
                    "post_id": response.post_id,
                    "message": "Image post published successfully",
                }, indent=2)
            )]
    
    except ValidationError as e:
        return [TextContent(
            type="text",
            text=json.dumps({
                "success": False,
                "error": "Validation error",
                "details": [{"field": err["loc"][0], "message": err["msg"]} for err in e.errors()],
            }, indent=2)
        )]
    
    except (ImageUploadError, PostCreationError) as e:
        return [TextContent(
            type="text",
            text=json.dumps({
                "success": False,
                "error": "Image post failed",
                "message": str(e),
            }, indent=2)
        )]
    
    except Exception as e:
        logger.error(f"Image post error: {e}")
        return [TextContent(
            type="text",
            text=json.dumps({
                "success": False,
                "error": type(e).__name__,
                "message": str(e),
            }, indent=2)
        )]


async def handle_fetch_comments(arguments: Dict[str, Any]) -> List[TextContent]:
    """Handle fetching post comments."""
    try:
        post_id = arguments["post_id"]
        limit = arguments.get("limit", 100)
        extract_keywords = arguments.get("extract_keywords", True)
        
        config = get_config()
        with FacebookManager(config=config) as manager:
            response = manager.get_post_comments(
                post_id=post_id,
                limit=limit,
                extract_keywords=extract_keywords
            )
            
            comments_data = [
                {
                    "comment_id": c.comment_id,
                    "author": c.from_user,
                    "message": c.message,
                    "created_time": c.created_time,
                    "like_count": c.like_count,
                    "reply_count": c.comment_count,
                    "is_hidden": c.is_hidden,
                }
                for c in response.comments
            ]
            
            result = {
                "success": True,
                "post_id": post_id,
                "total_comments": response.total_count,
                "comments_retrieved": len(comments_data),
                "comments": comments_data,
                "has_more": response.has_next_page,
            }
            
            if extract_keywords and response.keywords:
                result["keywords"] = response.keywords
            
            return [TextContent(
                type="text",
                text=json.dumps(result, indent=2)
            )]
    
    except FacebookAPIError as e:
        return [TextContent(
            type="text",
            text=json.dumps({
                "success": False,
                "error": "Facebook API error",
                "message": str(e),
            }, indent=2)
        )]
    
    except Exception as e:
        logger.error(f"Fetch comments error: {e}")
        return [TextContent(
            type="text",
            text=json.dumps({
                "success": False,
                "error": type(e).__name__,
                "message": str(e),
            }, indent=2)
        )]


async def handle_fetch_post_insights(arguments: Dict[str, Any]) -> List[TextContent]:
    """Handle fetching post insights."""
    try:
        post_id = arguments["post_id"]
        period_str = arguments.get("period", "lifetime")
        
        # Parse period
        period = InsightPeriod(period_str)
        
        config = get_config()
        with FacebookManager(config=config) as manager:
            insights = manager.get_post_insights(post_id=post_id, period=period)
            
            result = {
                "success": True,
                "post_id": insights.post_id,
                "period": insights.period.value,
                "reach": insights.reach,
                "impressions": insights.impressions,
                "reactions": {
                    "like": insights.reactions.like,
                    "love": insights.reactions.love,
                    "wow": insights.reactions.wow,
                    "haha": insights.reactions.haha,
                    "sad": insights.reactions.sad,
                    "angry": insights.reactions.angry,
                    "care": insights.reactions.care,
                    "total": insights.reactions.computed_total,
                },
                "comments_count": insights.comments_count,
                "shares_count": insights.shares_count,
                "clicked": insights.clicked,
                "engagement_rate": insights.engagement_rate,
            }
            
            return [TextContent(
                type="text",
                text=json.dumps(result, indent=2)
            )]
    
    except FacebookAPIError as e:
        return [TextContent(
            type="text",
            text=json.dumps({
                "success": False,
                "error": "Facebook API error",
                "message": str(e),
            }, indent=2)
        )]
    
    except Exception as e:
        logger.error(f"Fetch post insights error: {e}")
        return [TextContent(
            type="text",
            text=json.dumps({
                "success": False,
                "error": type(e).__name__,
                "message": str(e),
            }, indent=2)
        )]


async def handle_fetch_page_insights(arguments: Dict[str, Any]) -> List[TextContent]:
    """Handle fetching page insights."""
    try:
        period_str = arguments.get("period", "day")
        period = InsightPeriod(period_str)
        
        config = get_config()
        with FacebookManager(config=config) as manager:
            insights = manager.get_page_insights(period=period)
            
            result = {
                "success": True,
                "page_id": insights.page_id,
                "period": insights.period.value,
                "page_impressions": insights.page_impressions,
                "page_reach": insights.page_reach,
                "page_engaged_users": insights.page_engaged_users,
                "page_post_engagements": insights.page_post_engagements,
                "page_fans": insights.page_fans,
                "page_fans_online": insights.page_fans_online,
                "page_views_total": insights.page_views_total,
                "page_consumptions": insights.page_consumptions,
            }
            
            return [TextContent(
                type="text",
                text=json.dumps(result, indent=2)
            )]
    
    except FacebookAPIError as e:
        return [TextContent(
            type="text",
            text=json.dumps({
                "success": False,
                "error": "Facebook API error",
                "message": str(e),
            }, indent=2)
        )]
    
    except Exception as e:
        logger.error(f"Fetch page insights error: {e}")
        return [TextContent(
            type="text",
            text=json.dumps({
                "success": False,
                "error": type(e).__name__,
                "message": str(e),
            }, indent=2)
        )]


async def handle_reply_to_comment(arguments: Dict[str, Any]) -> List[TextContent]:
    """Handle replying to a comment."""
    try:
        comment_id = arguments["comment_id"]
        message = arguments["message"]
        
        config = get_config()
        request = CommentReplyRequest(comment_id=comment_id, message=message)
        
        with FacebookManager(config=config) as manager:
            response = manager.reply_to_comment(request)
            
            return [TextContent(
                type="text",
                text=json.dumps({
                    "success": response.success,
                    "comment_id": response.comment_id,
                    "action": response.action,
                    "message": response.message or "Reply posted successfully",
                }, indent=2)
            )]
    
    except FacebookAPIError as e:
        return [TextContent(
            type="text",
            text=json.dumps({
                "success": False,
                "error": "Facebook API error",
                "message": str(e),
            }, indent=2)
        )]
    
    except Exception as e:
        logger.error(f"Reply to comment error: {e}")
        return [TextContent(
            type="text",
            text=json.dumps({
                "success": False,
                "error": type(e).__name__,
                "message": str(e),
            }, indent=2)
        )]


async def handle_like_comment(arguments: Dict[str, Any]) -> List[TextContent]:
    """Handle liking a comment."""
    try:
        comment_id = arguments["comment_id"]
        
        config = get_config()
        request = CommentReactionRequest(comment_id=comment_id, reaction_type="LIKE")
        
        with FacebookManager(config=config) as manager:
            response = manager.react_to_comment(request)
            
            return [TextContent(
                type="text",
                text=json.dumps({
                    "success": response.success,
                    "comment_id": response.comment_id,
                    "action": response.action,
                    "message": "Comment liked successfully",
                }, indent=2)
            )]
    
    except FacebookAPIError as e:
        return [TextContent(
            type="text",
            text=json.dumps({
                "success": False,
                "error": "Facebook API error",
                "message": str(e),
            }, indent=2)
        )]
    
    except Exception as e:
        logger.error(f"Like comment error: {e}")
        return [TextContent(
            type="text",
            text=json.dumps({
                "success": False,
                "error": type(e).__name__,
                "message": str(e),
            }, indent=2)
        )]


async def handle_hide_comment(arguments: Dict[str, Any]) -> List[TextContent]:
    """Handle hiding a comment."""
    try:
        comment_id = arguments["comment_id"]
        
        config = get_config()
        with FacebookManager(config=config) as manager:
            response = manager.hide_comment(comment_id)
            
            return [TextContent(
                type="text",
                text=json.dumps({
                    "success": response.success,
                    "comment_id": response.comment_id,
                    "action": response.action,
                    "message": "Comment hidden successfully",
                }, indent=2)
            )]
    
    except FacebookAPIError as e:
        return [TextContent(
            type="text",
            text=json.dumps({
                "success": False,
                "error": "Facebook API error",
                "message": str(e),
            }, indent=2)
        )]
    
    except Exception as e:
        logger.error(f"Hide comment error: {e}")
        return [TextContent(
            type="text",
            text=json.dumps({
                "success": False,
                "error": type(e).__name__,
                "message": str(e),
            }, indent=2)
        )]


async def handle_delete_comment(arguments: Dict[str, Any]) -> List[TextContent]:
    """Handle deleting a comment."""
    try:
        comment_id = arguments["comment_id"]
        
        config = get_config()
        with FacebookManager(config=config) as manager:
            response = manager.delete_comment(comment_id)
            
            return [TextContent(
                type="text",
                text=json.dumps({
                    "success": response.success,
                    "comment_id": response.comment_id,
                    "action": response.action,
                    "message": "Comment deleted successfully",
                }, indent=2)
            )]
    
    except FacebookAPIError as e:
        return [TextContent(
            type="text",
            text=json.dumps({
                "success": False,
                "error": "Facebook API error",
                "message": str(e),
            }, indent=2)
        )]
    
    except Exception as e:
        logger.error(f"Delete comment error: {e}")
        return [TextContent(
            type="text",
            text=json.dumps({
                "success": False,
                "error": type(e).__name__,
                "message": str(e),
            }, indent=2)
        )]


async def handle_extract_keywords(arguments: Dict[str, Any]) -> List[TextContent]:
    """Handle extracting keywords from comments."""
    try:
        post_id = arguments["post_id"]
        top_n = arguments.get("top_n", 20)
        min_length = arguments.get("min_length", 3)
        
        config = get_config()
        with FacebookManager(config=config) as manager:
            # Fetch comments first
            response = manager.get_post_comments(
                post_id=post_id,
                limit=500,  # Get more for better analysis
                extract_keywords=False  # We'll extract manually
            )
            
            # Extract keywords
            keywords = manager.extract_keywords(
                response.comments,
                top_n=top_n
            )
            
            return [TextContent(
                type="text",
                text=json.dumps({
                    "success": True,
                    "post_id": post_id,
                    "total_comments_analyzed": len(response.comments),
                    "keywords": keywords,
                }, indent=2)
            )]
    
    except FacebookAPIError as e:
        return [TextContent(
            type="text",
            text=json.dumps({
                "success": False,
                "error": "Facebook API error",
                "message": str(e),
            }, indent=2)
        )]
    
    except Exception as e:
        logger.error(f"Extract keywords error: {e}")
        return [TextContent(
            type="text",
            text=json.dumps({
                "success": False,
                "error": type(e).__name__,
                "message": str(e),
            }, indent=2)
        )]


# =============================================================================
# MCP Server Handlers
# =============================================================================

@app.list_tools()
async def list_tools() -> List[Tool]:
    """List all available tools."""
    logger.info("Listing tools")
    return TOOLS


@app.call_tool()
async def call_tool(name: str, arguments: Any) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
    """Handle tool calls."""
    logger.info(f"Tool called: {name} with arguments: {arguments}")
    
    # Map tool names to handlers
    handlers = {
        "verify_facebook_credentials": handle_verify_credentials,
        "post_text_to_facebook": handle_post_text,
        "post_image_to_facebook": handle_post_image,
        "fetch_post_comments": handle_fetch_comments,
        "fetch_post_insights": handle_fetch_post_insights,
        "fetch_page_insights": handle_fetch_page_insights,
        "reply_to_comment": handle_reply_to_comment,
        "like_comment": handle_like_comment,
        "hide_comment": handle_hide_comment,
        "delete_comment": handle_delete_comment,
        "extract_comment_keywords": handle_extract_keywords,
    }
    
    handler = handlers.get(name)
    if not handler:
        logger.error(f"Unknown tool: {name}")
        return [TextContent(
            type="text",
            text=json.dumps({
                "success": False,
                "error": "Unknown tool",
                "message": f"Tool '{name}' is not recognized",
            }, indent=2)
        )]
    
    try:
        return await handler(arguments or {})
    except Exception as e:
        logger.error(f"Tool execution error for {name}: {e}", exc_info=True)
        return [TextContent(
            type="text",
            text=json.dumps({
                "success": False,
                "error": "Tool execution failed",
                "message": str(e),
            }, indent=2)
        )]


# =============================================================================
# Main Entry Point
# =============================================================================

async def main():
    """Run the MCP server."""
    logger.info("Starting Facebook Manager MCP Server")
    
    # Verify configuration on startup
    try:
        config = get_config()
        logger.info(f"Server initialized for Facebook Page: {config.facebook_page_id}")
    except Exception as e:
        logger.error(f"Failed to initialize server: {e}")
        logger.error("Please check your .env file and ensure FACEBOOK_PAGE_ID and FACEBOOK_ACCESS_TOKEN are set")
        sys.exit(1)
    
    # Run the stdio server
    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Server shutdown by user")
    except Exception as e:
        logger.error(f"Server error: {e}", exc_info=True)
        sys.exit(1)
