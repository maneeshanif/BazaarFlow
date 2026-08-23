"""
Facebook Manager Tool - Core API Client
Handles Facebook Graph API interactions for posting content
"""

import logging
import re
from typing import Optional, Dict, Any, List
from pathlib import Path
from collections import Counter
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

try:
    from .fb_config import FacebookConfig, get_config
    from .fb_model import (
        TextPostRequest,
        ImagePostRequest,
        VideoPostRequest,
        FacebookPostResponse,
        FacebookErrorResponse,
        PostType,
        CommentData,
        CommentsResponse,
        CommentReplyRequest,
        CommentReactionRequest,
        CommentActionResponse,
        ReactionType,
        PostInsights,
        PageInsights,
        ReactionBreakdown,
        InsightPeriod,
    )
    
except ImportError:  # pragma: no cover - fallback for script-style imports
    from config.fb_config import FacebookConfig, get_config
    from models.fb_model import (
        TextPostRequest,
        ImagePostRequest,
        VideoPostRequest,
        FacebookPostResponse,
        FacebookErrorResponse,
        PostType,
        CommentData,
        CommentsResponse,
        CommentReplyRequest,
        CommentReactionRequest,
        CommentActionResponse,
        ReactionType,
        PostInsights,
        PageInsights,
        ReactionBreakdown,
        InsightPeriod,
    )
    from src.exceptions import (
        FacebookAPIError,
        InvalidCredentialsError,
        PostCreationError,
        ImageUploadError,
    )


logger = logging.getLogger(__name__)


class FacebookManager:
    """
    Main Facebook Manager class for handling page operations.
    Provides methods for creating posts with text and images.
    """
    
    def __init__(self, config: Optional[FacebookConfig] = None):
        """
        Initialize Facebook Manager.
        
        Args:
            config: Optional FacebookConfig instance. If None, loads from environment.
        """
        self.config = config or get_config()
        self.session = self._create_session()
        
        logger.info(f"Facebook Manager initialized for page: {self.config.facebook_page_id}")
    
    def _create_session(self) -> requests.Session:
        """
        Create a requests session with retry logic.
        
        Returns:
            Configured requests.Session instance
        """
        session = requests.Session()
        
        # Configure retry strategy
        retry_strategy = Retry(
            total=self.config.max_retries,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "POST", "PUT", "DELETE", "OPTIONS", "TRACE"]
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        return session
    
    def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        files: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Make an HTTP request to Facebook Graph API.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint (relative to base URL)
            data: Optional form data
            files: Optional files to upload
            params: Optional query parameters
            
        Returns:
            Response data as dictionary
            
        Raises:
            FacebookAPIError: If the API request fails
        """
        url = f"{self.config.graph_api_url}/{endpoint}"
        
        # Add access token to parameters
        if params is None:
            params = {}
        params['access_token'] = self.config.facebook_access_token
        
        try:
            response = self.session.request(
                method=method,
                url=url,
                data=data,
                files=files,
                params=params,
                timeout=self.config.request_timeout
            )
            
            response_data = response.json()
            
            # Check for errors in response
            if 'error' in response_data:
                error = response_data['error']
                error_response = FacebookErrorResponse(
                    error_code=error.get('code', 0),
                    error_message=error.get('message', 'Unknown error'),
                    error_type=error.get('type', 'UnknownError'),
                    error_subcode=error.get('error_subcode')
                )
                
                logger.error(f"Facebook API Error: {error_response.error_message}")
                
                # Raise specific error based on error code
                if error_response.error_code == 190:
                    raise InvalidCredentialsError(error_response.error_message)
                else:
                    raise FacebookAPIError(
                        error_response.error_message,
                        error_response.error_code
                    )
            
            return response_data
            
        except requests.exceptions.Timeout:
            logger.error(f"Request timeout for endpoint: {endpoint}")
            raise FacebookAPIError(f"Request timeout after {self.config.request_timeout}s")
        
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {str(e)}")
            raise FacebookAPIError(f"Request failed: {str(e)}")
    
    def create_text_post(self, post_request: TextPostRequest) -> FacebookPostResponse:
        """
        Create a text-only post on the Facebook page.
        
        Args:
            post_request: TextPostRequest with post content
            
        Returns:
            FacebookPostResponse with post ID
            
        Raises:
            PostCreationError: If post creation fails
        """
        try:
            logger.info("Creating text post...")
            
            data = {
                'message': post_request.message
            }
            
            response = self._make_request(
                method='POST',
                endpoint=f"{self.config.facebook_page_id}/feed",
                data=data
            )
            
            post_id = response.get('id')
            
            if not post_id:
                raise PostCreationError("No post ID returned from Facebook")
            
            logger.info(f"Text post created successfully: {post_id}")
            
            return FacebookPostResponse(
                post_id=post_id,
                success=True,
                message="Text post created successfully"
            )
            
        except FacebookAPIError as e:
            logger.error(f"Failed to create text post: {str(e)}")
            raise PostCreationError(f"Failed to create text post: {str(e)}")
    
    def create_image_post(self, post_request: ImagePostRequest) -> FacebookPostResponse:
        """
        Create a post with an image on the Facebook page.
        Supports both URL-based and file-based image uploads.
        
        Args:
            post_request: ImagePostRequest with image and optional text
            
        Returns:
            FacebookPostResponse with post ID
            
        Raises:
            ImageUploadError: If image upload fails
            PostCreationError: If post creation fails
        """
        try:
            logger.info("Creating image post...")
            
            if post_request.image_url:
                # URL-based image upload
                return self._create_image_post_from_url(post_request)
            elif post_request.image_path:
                # File-based image upload
                return self._create_image_post_from_file(post_request)
            else:
                raise ImageUploadError("No image source provided")
                
        except FacebookAPIError as e:
            logger.error(f"Failed to create image post: {str(e)}")
            raise PostCreationError(f"Failed to create image post: {str(e)}")
    
    def _create_image_post_from_url(
        self, 
        post_request: ImagePostRequest
    ) -> FacebookPostResponse:
        """
        Create an image post using an image URL.
        
        Args:
            post_request: ImagePostRequest with image_url
            
        Returns:
            FacebookPostResponse with post ID
        """
        data = {
            'url': str(post_request.image_url),
            'published': 'true'
        }
        
        if post_request.message:
            data['message'] = post_request.message
        
        response = self._make_request(
            method='POST',
            endpoint=f"{self.config.facebook_page_id}/photos",
            data=data
        )
        
        post_id = response.get('post_id') or response.get('id')
        
        if not post_id:
            raise ImageUploadError("No post ID returned from Facebook")
        
        logger.info(f"Image post created successfully from URL: {post_id}")
        
        return FacebookPostResponse(
            post_id=post_id,
            success=True,
            message="Image post created successfully from URL"
        )
    
    def _create_image_post_from_file(
        self, 
        post_request: ImagePostRequest
    ) -> FacebookPostResponse:
        """
        Create an image post by uploading a local file.
        
        Args:
            post_request: ImagePostRequest with image_path
            
        Returns:
            FacebookPostResponse with post ID
        """
        image_path = Path(post_request.image_path)
        
        # Validate file exists
        if not image_path.exists():
            raise ImageUploadError(f"Image file not found: {post_request.image_path}")
        
        # Validate file is an image
        valid_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'}
        if image_path.suffix.lower() not in valid_extensions:
            raise ImageUploadError(
                f"Invalid image format: {image_path.suffix}. "
                f"Supported formats: {', '.join(valid_extensions)}"
            )
        
        # Prepare data
        data = {'published': 'true'}
        if post_request.message:
            data['message'] = post_request.message
        
        # Open and upload file
        with open(image_path, 'rb') as image_file:
            files = {
                'source': (image_path.name, image_file, self._get_mime_type(image_path))
            }
            
            response = self._make_request(
                method='POST',
                endpoint=f"{self.config.facebook_page_id}/photos",
                data=data,
                files=files
            )
        
        post_id = response.get('post_id') or response.get('id')
        
        if not post_id:
            raise ImageUploadError("No post ID returned from Facebook")
        
        logger.info(f"Image post created successfully from file: {post_id}")
        
        return FacebookPostResponse(
            post_id=post_id,
            success=True,
            message="Image post created successfully from file"
        )
    
    def _get_mime_type(self, file_path: Path) -> str:
        """
        Get MIME type for an image file.
        
        Args:
            file_path: Path to the image file
            
        Returns:
            MIME type string
        """
        mime_types = {
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.gif': 'image/gif',
            '.bmp': 'image/bmp',
            '.webp': 'image/webp'
        }
        return mime_types.get(file_path.suffix.lower(), 'application/octet-stream')
    
    def verify_credentials(self) -> bool:
        """
        Verify that the configured credentials are valid.
        
        Returns:
            True if credentials are valid
            
        Raises:
            InvalidCredentialsError: If credentials are invalid
        """
        try:
            logger.info("Verifying Facebook credentials...")
            
            response = self._make_request(
                method='GET',
                endpoint=self.config.facebook_page_id,
                params={'fields': 'id,name'}
            )
            
            page_name = response.get('name', 'Unknown')
            logger.info(f"Credentials verified successfully for page: {page_name}")
            
            return True
            
        except FacebookAPIError as e:
            logger.error(f"Credential verification failed: {str(e)}")
            raise InvalidCredentialsError(f"Invalid credentials: {str(e)}")
    
    def normalize_post_id(self, raw_post_id: str) -> str:
        """Normalize the post identifier for Graph API operations."""

        if "_" in raw_post_id:
            return raw_post_id

        try:
            response = self._make_request(
                method="GET",
                endpoint=raw_post_id,
                params={"fields": "post_id,id"}
            )

            post_id = response.get("post_id") or response.get("id")
            if isinstance(post_id, str) and "_" in post_id:
                logger.debug("Resolved raw post id %s to feed id %s", raw_post_id, post_id)
                return post_id
        except FacebookAPIError as exc:
            logger.debug("Could not resolve raw post id %s via direct lookup: %s", raw_post_id, exc)

        candidate = f"{self.config.facebook_page_id}_{raw_post_id}"
        if "_" in candidate:
            try:
                self._make_request(
                    method="GET",
                    endpoint=candidate,
                    params={"fields": "id"}
                )
                logger.debug("Using page-prefixed candidate %s for post %s", candidate, raw_post_id)
                return candidate
            except FacebookAPIError as exc:
                logger.debug(
                    "Prefixed lookup for post id %s (%s) failed: %s", raw_post_id, candidate, exc
                )

        return raw_post_id

    def get_post(self, post_id: str) -> Dict[str, Any]:
        """
        Retrieve details about a specific post.
        
        Args:
            post_id: The Facebook post ID
            
        Returns:
            Post data as dictionary
            
        Raises:
            FacebookAPIError: If request fails
        """
        try:
            logger.info(f"Retrieving post: {post_id}")
            
            normalized_id = self.normalize_post_id(post_id)

            response = self._make_request(
                method='GET',
                endpoint=normalized_id,
                params={'fields': 'id,permalink_url,created_time'}
            )
            
            return response
            
        except FacebookAPIError as e:
            logger.error(f"Failed to retrieve post: {str(e)}")
            raise

    def delete_post(self, post_id: str) -> bool:
        """Delete a post from the configured Facebook page."""

        try:
            normalized_id = self.normalize_post_id(post_id)
            logger.info(f"Deleting post: {normalized_id}")
            response = self._make_request(method="DELETE", endpoint=normalized_id)
            success = response.get("success")
            if success is None:
                return True
            return bool(success)
        except FacebookAPIError as e:
            if normalized_id != post_id:
                logger.debug(
                    "Delete via normalized id %s failed (%s); retrying with raw id %s",
                    normalized_id,
                    e,
                    post_id,
                )
                try:
                    response = self._make_request(method="DELETE", endpoint=post_id)
                    success = response.get("success")
                    if success is None:
                        return True
                    return bool(success)
                except FacebookAPIError as inner_exc:
                    logger.debug("Fallback delete using %s also failed: %s", post_id, inner_exc)
            logger.error(f"Failed to delete post: {str(e)}")
            raise
    
    # ========================================================================
    # COMMENT MANAGEMENT METHODS
    # ========================================================================
    
    def get_post_comments(
        self,
        post_id: str,
        limit: int = 100,
        extract_keywords: bool = True,
        min_keyword_length: int = 3,
        top_keywords: int = 20
    ) -> CommentsResponse:
        """
        Retrieve comments for a specific post with optional keyword extraction.
        
        Args:
            post_id: The Facebook post ID
            limit: Maximum number of comments to retrieve (default: 100)
            extract_keywords: Whether to extract keywords from comments (default: True)
            min_keyword_length: Minimum length for keywords (default: 3)
            top_keywords: Number of top keywords to return (default: 20)
            
        Returns:
            CommentsResponse with comments and optionally extracted keywords
            
        Raises:
            FacebookAPIError: If request fails
        """
        try:
            normalized_post_id = self.normalize_post_id(post_id)

            logger.info(f"Retrieving comments for post: {normalized_post_id}")
            
            params = {
                'fields': 'id,message,from,created_time,like_count,comment_count,is_hidden,parent,attachment',
                'limit': min(limit, 100),  # Facebook API limit per request
                'order': 'reverse_chronological'
            }
            
            response = self._make_request(
                method='GET',
                endpoint=f"{normalized_post_id}/comments",
                params=params
            )
            
            comments_data = response.get('data', [])
            paging = response.get('paging', {})
            
            # Parse comments
            comments = []
            all_text = []
            
            for comment_data in comments_data:
                comment = CommentData(
                    comment_id=comment_data.get('id'),
                    post_id=normalized_post_id,
                    message=comment_data.get('message', ''),
                    from_user=comment_data.get('from', {}),
                    created_time=comment_data.get('created_time', ''),
                    like_count=comment_data.get('like_count', 0),
                    comment_count=comment_data.get('comment_count', 0),
                    is_hidden=comment_data.get('is_hidden', False),
                    parent_comment_id=comment_data.get('parent', {}).get('id') if comment_data.get('parent') else None,
                    attachment=comment_data.get('attachment')
                )
                comments.append(comment)
                all_text.append(comment.message)
            
            # Extract keywords if requested
            keywords = []
            if extract_keywords and all_text:
                keywords = self._extract_keywords(
                    all_text,
                    min_length=min_keyword_length,
                    top_n=top_keywords
                )
            
            return CommentsResponse(
                comments=comments,
                total_count=len(comments),
                has_next_page='next' in paging,
                next_cursor=paging.get('cursors', {}).get('after'),
                keywords=keywords
            )
            
        except FacebookAPIError as e:
            logger.error(f"Failed to retrieve comments: {str(e)}")
            raise
    
    def _extract_keywords(
        self,
        texts: List[str],
        min_length: int = 3,
        top_n: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Extract keywords from a list of text strings using frequency analysis.
        
        Args:
            texts: List of text strings to analyze
            min_length: Minimum word length to consider (default: 3)
            top_n: Number of top keywords to return (default: 20)
            
        Returns:
            List of dictionaries with keyword and frequency
        """
        # Common stop words to filter out
        stop_words = {
            'the', 'is', 'at', 'which', 'on', 'in', 'a', 'an', 'and', 'or', 'but',
            'to', 'for', 'of', 'as', 'by', 'with', 'from', 'this', 'that', 'these',
            'those', 'it', 'its', 'be', 'are', 'was', 'were', 'been', 'have', 'has',
            'had', 'do', 'does', 'did', 'will', 'would', 'should', 'could', 'may',
            'might', 'must', 'can', 'am', 'i', 'you', 'he', 'she', 'we', 'they',
            'my', 'your', 'his', 'her', 'our', 'their', 'me', 'him', 'us', 'them'
        }
        
        # Extract all words
        all_words = []
        for text in texts:
            # Remove URLs, mentions, hashtags first
            cleaned = re.sub(r'http\S+|www\S+|@\w+|#\w+', '', text.lower())
            # Extract words (alphanumeric only)
            words = re.findall(r'\b[a-z0-9]+\b', cleaned)
            # Filter by length and stop words
            filtered = [w for w in words if len(w) >= min_length and w not in stop_words]
            all_words.extend(filtered)
        
        # Count frequencies
        word_freq = Counter(all_words)
        
        # Get top N keywords
        top_keywords = word_freq.most_common(top_n)
        
        return [
            {"keyword": word, "frequency": freq}
            for word, freq in top_keywords
        ]
    
    def reply_to_comment(self, reply_request: CommentReplyRequest) -> CommentActionResponse:
        """
        Reply to a comment on a post.
        
        Args:
            reply_request: CommentReplyRequest with comment ID and reply message
            
        Returns:
            CommentActionResponse with action result
            
        Raises:
            FacebookAPIError: If request fails
        """
        try:
            logger.info(f"Replying to comment: {reply_request.comment_id}")
            
            data = {
                'message': reply_request.message
            }
            
            response = self._make_request(
                method='POST',
                endpoint=f"{reply_request.comment_id}/comments",
                data=data
            )
            
            reply_id = response.get('id')
            
            return CommentActionResponse(
                success=True,
                comment_id=reply_request.comment_id,
                action="reply",
                message=f"Reply posted successfully with ID: {reply_id}"
            )
            
        except FacebookAPIError as e:
            logger.error(f"Failed to reply to comment: {str(e)}")
            raise
    
    def react_to_comment(self, reaction_request: CommentReactionRequest) -> CommentActionResponse:
        """
        React/like a comment.
        
        Args:
            reaction_request: CommentReactionRequest with comment ID and reaction type
            
        Returns:
            CommentActionResponse with action result
            
        Raises:
            FacebookAPIError: If request fails
        """
        try:
            logger.info(f"Reacting to comment: {reaction_request.comment_id}")
            
            data = {
                'type': reaction_request.reaction_type.value
            }
            
            response = self._make_request(
                method='POST',
                endpoint=f"{reaction_request.comment_id}/likes",
                data=data
            )
            
            return CommentActionResponse(
                success=response.get('success', True),
                comment_id=reaction_request.comment_id,
                action="react",
                message=f"Reacted with {reaction_request.reaction_type.value}"
            )
            
        except FacebookAPIError as e:
            logger.error(f"Failed to react to comment: {str(e)}")
            raise
    
    def hide_comment(self, comment_id: str) -> CommentActionResponse:
        """
        Hide a comment (makes it visible only to the commenter and their friends).
        
        Args:
            comment_id: ID of the comment to hide
            
        Returns:
            CommentActionResponse with action result
            
        Raises:
            FacebookAPIError: If request fails
        """
        try:
            logger.info(f"Hiding comment: {comment_id}")
            
            data = {
                'is_hidden': 'true'
            }
            
            response = self._make_request(
                method='POST',
                endpoint=comment_id,
                data=data
            )
            
            return CommentActionResponse(
                success=response.get('success', True),
                comment_id=comment_id,
                action="hide",
                message="Comment hidden successfully"
            )
            
        except FacebookAPIError as e:
            logger.error(f"Failed to hide comment: {str(e)}")
            raise
    
    def delete_comment(self, comment_id: str) -> CommentActionResponse:
        """
        Delete a comment permanently.
        
        Args:
            comment_id: ID of the comment to delete
            
        Returns:
            CommentActionResponse with action result
            
        Raises:
            FacebookAPIError: If request fails
        """
        try:
            logger.info(f"Deleting comment: {comment_id}")
            
            response = self._make_request(
                method='DELETE',
                endpoint=comment_id
            )
            
            return CommentActionResponse(
                success=response.get('success', True),
                comment_id=comment_id,
                action="delete",
                message="Comment deleted successfully"
            )
            
        except FacebookAPIError as e:
            logger.error(f"Failed to delete comment: {str(e)}")
            raise
    
    # ========================================================================
    # INSIGHTS & ANALYTICS METHODS
    # ========================================================================
    
    def get_post_insights(
        self,
        post_id: str,
        period: InsightPeriod = InsightPeriod.LIFETIME
    ) -> PostInsights:
        """
        Get insights/analytics for a specific post.
        
        Args:
            post_id: The Facebook post ID
            period: Requested time period. Post-level metrics used here are
                lifetime-only, so the value will be coerced to InsightPeriod.LIFETIME.
            
        Returns:
            PostInsights with engagement metrics
            
        Raises:
            FacebookAPIError: If request fails
        """
        try:
            normalized_post_id = self.normalize_post_id(post_id)

            if period != InsightPeriod.LIFETIME:
                logger.debug(
                    "Post insights metrics are lifetime-only; overriding requested period %s to lifetime.",
                    period.value
                )
            logger.info(f"Retrieving insights for post: {post_id} (period: lifetime)")

            metrics_to_fetch = [
                'post_impressions',
                'post_impressions_unique',
                'post_clicks',
                'post_reactions_by_type_total',
                'post_activity_by_action_type_unique'
            ]

            insights_response = self._make_request(
                method='GET',
                endpoint=f"{normalized_post_id}/insights",
                params={
                    'metric': ','.join(metrics_to_fetch),
                    'period': InsightPeriod.LIFETIME.value
                }
            )

            comments_count = 0
            shares_count = 0

            try:
                post_details = self._make_request(
                    method='GET',
                    endpoint=normalized_post_id,
                    params={'fields': 'shares,comments.summary(true)'}
                )

                comments_count = post_details.get('comments', {}).get('summary', {}).get('total_count', 0)
                shares_count = post_details.get('shares', {}).get('count', 0)
            except FacebookAPIError as details_error:
                if getattr(details_error, 'error_code', None) == 100:
                    logger.debug(
                        "Shares/comments detail unavailable for %s: %s",
                        normalized_post_id,
                        details_error
                    )
                else:
                    raise

            metrics: Dict[str, Any] = {}
            for insight in insights_response.get('data', []):
                metric_name = insight.get('name')
                values = insight.get('values', [])
                if not metric_name or not values:
                    continue
                metrics[metric_name] = values[-1].get('value')

            reaction_breakdown = self._build_reaction_breakdown_from_insights(
                metrics.get('post_reactions_by_type_total')
            )

            if reaction_breakdown is None:
                reactions_response = self._make_request(
                    method='GET',
                    endpoint=f"{normalized_post_id}/reactions",
                    params={'summary': 'total_count', 'limit': 0}
                )
                reaction_breakdown = self._parse_reaction_breakdown(
                    reactions_response.get('data', [])
                )

            reach = metrics.get('post_impressions_unique', 0) or 0
            impressions = metrics.get('post_impressions', 0) or 0
            clicks = metrics.get('post_clicks', 0) or 0

            total_engagement = (
                reaction_breakdown.total
                + comments_count
                + shares_count
                + clicks
            )
            engagement_rate = 0.0
            if reach:
                engagement_rate = (total_engagement / reach) * 100

            return PostInsights(
                post_id=normalized_post_id,
                period=InsightPeriod.LIFETIME,
                reach=reach,
                impressions=impressions,
                reactions=reaction_breakdown,
                comments_count=comments_count,
                shares_count=shares_count,
                engagement_rate=round(engagement_rate, 2),
                clicked=clicks
            )

        except FacebookAPIError as e:
            logger.error(f"Failed to retrieve post insights: {str(e)}")
            raise
    
    def _build_reaction_breakdown_from_insights(
        self,
        reaction_values: Any
    ) -> Optional[ReactionBreakdown]:
        """Build a reaction breakdown from insights metric data if available."""
        if not isinstance(reaction_values, dict):
            return None

        like = int(reaction_values.get('like', 0) or 0)
        love = int(reaction_values.get('love', 0) or 0)
        wow = int(reaction_values.get('wow', 0) or 0)
        haha = int(reaction_values.get('haha', 0) or 0)
        sad = int(
            reaction_values.get('sad', reaction_values.get('sorry', 0)) or 0
        )
        angry = int(
            reaction_values.get('angry', reaction_values.get('anger', 0)) or 0
        )
        care = int(reaction_values.get('care', 0) or 0)

        total = like + love + wow + haha + sad + angry + care

        return ReactionBreakdown(
            like=like,
            love=love,
            wow=wow,
            haha=haha,
            sad=sad,
            angry=angry,
            care=care,
            total=total
        )

    def _parse_reaction_breakdown(self, reactions_data: List[Dict]) -> ReactionBreakdown:
        """
        Parse reactions data into ReactionBreakdown model.
        
        Args:
            reactions_data: List of reaction data from API
            
        Returns:
            ReactionBreakdown with counts by type
        """
        reaction_counts = {
            'like': 0,
            'love': 0,
            'wow': 0,
            'haha': 0,
            'sad': 0,
            'angry': 0,
            'care': 0
        }
        
        for reaction in reactions_data:
            reaction_type = reaction.get('type', '').lower()
            if reaction_type in reaction_counts:
                reaction_counts[reaction_type] += 1
        
        total = sum(reaction_counts.values())
        
        return ReactionBreakdown(
            like=reaction_counts['like'],
            love=reaction_counts['love'],
            wow=reaction_counts['wow'],
            haha=reaction_counts['haha'],
            sad=reaction_counts['sad'],
            angry=reaction_counts['angry'],
            care=reaction_counts['care'],
            total=total
        )
    
    def get_page_insights(
        self,
        period: InsightPeriod = InsightPeriod.LAST_24_HOURS
    ) -> PageInsights:
        """
        Get insights/analytics for the entire page.
        
        Args:
            period: Time period for insights (LAST_24_HOURS or LAST_7_DAYS)
            
        Returns:
            PageInsights with page-level metrics
            
        Raises:
            FacebookAPIError: If request fails
        """
        try:
            api_period = period
            if period == InsightPeriod.LIFETIME:
                api_period = InsightPeriod.LAST_28_DAYS
                logger.debug(
                    "Page insights do not support lifetime period; falling back to %s.",
                    api_period.value
                )

            logger.info(f"Retrieving page insights (period: {api_period.value})")
            
            metrics = [
                'page_impressions',
                'page_impressions_unique',
                'page_engaged_users',
                'page_post_engagements',
                'page_fans',
                'page_views_total'
            ]
            
            insights_params = {
                'metric': ','.join(metrics),
                'period': api_period.value
            }
            
            insights_response = self._make_request(
                method='GET',
                endpoint=f"{self.config.facebook_page_id}/insights",
                params=insights_params
            )
            
            # Parse insights data
            parsed_metrics: Dict[str, Any] = {}
            for insight in insights_response.get('data', []):
                metric_name = insight.get('name')
                values = insight.get('values', [])
                if values:
                    last_value = values[-1].get('value', 0)
                    parsed_metrics[metric_name] = last_value
            
            return PageInsights(
                page_id=self.config.facebook_page_id,
                period=api_period,
                page_impressions=parsed_metrics.get('page_impressions', 0),
                page_reach=parsed_metrics.get('page_impressions_unique', 0),
                page_engaged_users=parsed_metrics.get('page_engaged_users', 0),
                page_post_engagements=parsed_metrics.get('page_post_engagements', 0),
                page_fans=parsed_metrics.get('page_fans', 0),
                page_fans_online=parsed_metrics.get('page_fans_online', 0),
                page_views_total=parsed_metrics.get('page_views_total', 0),
                page_consumptions=parsed_metrics.get('page_consumptions', 0)
            )
            
        except FacebookAPIError as e:
            logger.error(f"Failed to retrieve page insights: {str(e)}")
            raise
    
    def extract_keywords(
        self,
        comments: List[CommentData],
        top_n: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Extract keywords/topics from a list of comments using frequency analysis.
        
        This is a simple, non-AI approach that identifies the most frequent
        meaningful words in comments.
        
        Args:
            comments: List of CommentData objects
            top_n: Number of top keywords to return
            
        Returns:
            List of dictionaries with 'keyword' and 'count' keys
        """
        from collections import Counter
        import re
        
        # Common stop words to filter out
        stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'were', 'been',
            'be', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would',
            'should', 'could', 'may', 'might', 'must', 'can', 'this', 'that',
            'these', 'those', 'i', 'you', 'he', 'she', 'it', 'we', 'they',
            'my', 'your', 'his', 'her', 'its', 'our', 'their', 'what', 'which',
            'who', 'when', 'where', 'why', 'how', 'all', 'each', 'every', 'both',
            'few', 'more', 'most', 'other', 'some', 'such', 'no', 'nor', 'not',
            'only', 'own', 'same', 'so', 'than', 'too', 'very', 'just', 'am'
        }
        
        # Collect all words from comments
        word_counts = Counter()
        
        for comment in comments:
            # Convert to lowercase and extract words
            words = re.findall(r'\b[a-z]{3,}\b', comment.message.lower())
            
            # Filter out stop words and short words
            meaningful_words = [w for w in words if w not in stop_words]
            
            # Update counter
            word_counts.update(meaningful_words)
        
        # Get top N keywords
        top_keywords = [
            {'keyword': word, 'count': count}
            for word, count in word_counts.most_common(top_n)
        ]
        
        logger.info(f"Extracted {len(top_keywords)} keywords from {len(comments)} comments")
        
        return top_keywords
    
    def close(self):
        """Close the HTTP session."""
        if self.session:
            self.session.close()
            logger.info("Facebook Manager session closed")
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()