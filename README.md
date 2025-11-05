# Facebook Manager Tool

A robust, type-safe Python tool for managing Facebook page posts and interactions. Built specifically for multi-agent systems with comprehensive validation, error handling, and testing.

## 🚀 Features

### Content Publishing
- ✅ **Text Posts**: Create simple text posts on your Facebook page
- ✅ **Image Posts**: Post images from URLs or local files

### Comment Management & Analytics
- ✅ **Comment Retrieval**: Get comments from specific posts with pagination
- ✅ **Keyword Extraction**: Analyze comments and extract trending topics (frequency-based)
- ✅ **Comment Actions**: Reply, like, hide, and delete comments
- ✅ **Post Insights**: Track reach, impressions, reactions breakdown, shares (24h & 7d periods)
- ✅ **Page Insights**: Monitor page-level engagement and growth metrics

### Developer Experience
- ✅ **Type-Safe**: Built with Pydantic for comprehensive data validation
- ✅ **Robust Error Handling**: Comprehensive exception handling with detailed error messages
- ✅ **Configuration Management**: Secure credential handling via environment variables
- ✅ **Fully Tested**: 80+ unit and integration tests
- ✅ **Context Manager Support**: Clean resource management
- ✅ **Retry Logic**: Automatic retry for transient failures

### Future Roadmap
- 🔄 **Planned**: Video posts, advanced AI-powered sentiment analysis, post scheduling

## 📋 Requirements

- Python 3.8+
- Facebook Page with Admin access
- Facebook Page Access Token

## 📦 Installation

1. **Clone the repository** (or copy the project files)

```bash
git clone <repository-url>
cd spec_drive_development
```

2. **Install dependencies**

```bash
pip install -r requirements.txt
```

3. **Configure environment variables**

Create a `.env` file in the project root:

```env
FACEBOOK_PAGE_ID=your_page_id_here
FACEBOOK_ACCESS_TOKEN=your_access_token_here
FACEBOOK_API_VERSION=v18.0  # Optional, defaults to v18.0
```

### Getting Your Facebook Credentials

#### 1. **Facebook Page ID**
   - Go to your Facebook Page
   - Click "About" in the left sidebar
   - Scroll down to find "Page ID"

#### 2. **Facebook Access Token**
   - Visit [Facebook Developers](https://developers.facebook.com/)
   - Create an App (or use existing)
   - Go to Tools & Support > Graph API Explorer
   - Select your app and page
   - Request permissions: `pages_manage_posts`, `pages_read_engagement`, `pages_manage_engagement`
   - Generate token and copy the Page Access Token

**⚠️ Important:** Never commit your `.env` file to version control!

## 🎯 Quick Start

### Basic Text Post

```python
from src import FacebookManager, TextPostRequest

# Initialize manager (loads from .env automatically)
with FacebookManager() as manager:
    # Create a text post
    post = TextPostRequest(message="Hello, Facebook! 🚀")
    response = manager.create_text_post(post)
    
    print(f"Post created: {response.post_id}")
```

### Image Post from URL

```python
from src import FacebookManager, ImagePostRequest

with FacebookManager() as manager:
    # Create an image post from URL
    post = ImagePostRequest(
        message="Check out this image! 🖼️",
        image_url="https://example.com/image.jpg"
    )
    response = manager.create_image_post(post)
    
    print(f"Post created: {response.post_id}")
```

### Get Comments and Analyze

```python
from src import FacebookManager

with FacebookManager() as manager:
    # Get comments from a post
    comments = manager.get_post_comments(post_id="123456789_987654321", limit=50)
    
    print(f"Retrieved {len(comments.comments)} comments")
    
    # Extract keywords from comments
    keywords = manager.extract_keywords(comments.comments, top_n=10)
    
    for keyword, count in keywords:
        print(f"{keyword}: {count} mentions")
```

### Reply to Comments

```python
from src import FacebookManager, CommentReplyRequest

with FacebookManager() as manager:
    # Reply to a comment
    reply = CommentReplyRequest(
        comment_id="comment_123",
        message="Thank you for your feedback!"
    )
    response = manager.reply_to_comment(reply)
    
    print(f"Reply posted: {response.comment_id}")
```

### Get Post Insights

```python
from src import FacebookManager, InsightPeriod

with FacebookManager() as manager:
    # Get 24-hour insights
    insights = manager.get_post_insights(
        post_id="123456789_987654321",
        period=InsightPeriod.LAST_24_HOURS
    )
    
    print(f"Reach: {insights.reach}")
    print(f"Engagement Rate: {insights.engagement_rate}%")
    print(f"Total Reactions: {insights.reactions.computed_total}")
```

## 📚 API Reference

### FacebookManager

Main class for interacting with Facebook Graph API.

#### Methods

##### Content Publishing

##### `__init__(config: Optional[FacebookConfig] = None)`
Initialize the Facebook Manager.

**Parameters:**
- `config`: Optional FacebookConfig instance. If None, loads from environment.

##### `create_text_post(post_request: TextPostRequest) -> FacebookPostResponse`
Create a text-only post on the Facebook page.

**Parameters:**
- `post_request`: TextPostRequest with post content

**Returns:**
- FacebookPostResponse with post ID and status

**Raises:**
- `PostCreationError`: If post creation fails
- `InvalidCredentialsError`: If credentials are invalid

##### `create_image_post(post_request: ImagePostRequest) -> FacebookPostResponse`
Create a post with an image.

**Parameters:**
- `post_request`: ImagePostRequest with image and optional text

**Returns:**
- FacebookPostResponse with post ID and status

**Raises:**
- `ImageUploadError`: If image upload fails
- `PostCreationError`: If post creation fails

##### Comment Management

##### `get_post_comments(post_id: str, limit: int = 100) -> CommentsResponse`
Retrieve comments from a specific post.

**Parameters:**
- `post_id`: The Facebook post ID
- `limit`: Maximum number of comments to retrieve (default: 100)

**Returns:**
- CommentsResponse with list of CommentData objects

**Raises:**
- `FacebookAPIError`: If comment retrieval fails

##### `extract_keywords(comments: List[CommentData], top_n: int = 10) -> List[Tuple[str, int]]`
Extract most frequently mentioned keywords from comments.

**Parameters:**
- `comments`: List of CommentData objects
- `top_n`: Number of top keywords to return (default: 10)

**Returns:**
- List of tuples (keyword, frequency) sorted by frequency

##### `reply_to_comment(request: CommentReplyRequest) -> CommentActionResponse`
Reply to a specific comment.

**Parameters:**
- `request`: CommentReplyRequest with comment ID and reply message

**Returns:**
- CommentActionResponse with reply status

**Raises:**
- `FacebookAPIError`: If reply fails

##### `react_to_comment(request: CommentReactionRequest) -> CommentActionResponse`
React to (like) a comment.

**Parameters:**
- `request`: CommentReactionRequest with comment ID

**Returns:**
- CommentActionResponse with reaction status

**Raises:**
- `FacebookAPIError`: If reaction fails

##### `hide_comment(comment_id: str) -> CommentActionResponse`
Hide a comment from public view (still visible to commenter and friends).

**Parameters:**
- `comment_id`: The comment ID to hide

**Returns:**
- CommentActionResponse with hide status

**Raises:**
- `FacebookAPIError`: If hiding fails

##### `delete_comment(comment_id: str) -> CommentActionResponse`
Permanently delete a comment.

**Parameters:**
- `comment_id`: The comment ID to delete

**Returns:**
- CommentActionResponse with deletion status

**Raises:**
- `FacebookAPIError`: If deletion fails

##### Analytics & Insights

##### `get_post_insights(post_id: str, period: InsightPeriod = InsightPeriod.LAST_24_HOURS) -> PostInsights`
Get engagement metrics for a specific post.

**Parameters:**
- `post_id`: The Facebook post ID
- `period`: Time period (LAST_24_HOURS or LAST_7_DAYS)

**Returns:**
- PostInsights with reach, impressions, reactions, shares, etc.

**Raises:**
- `FacebookAPIError`: If insights retrieval fails

##### `get_page_insights(period: InsightPeriod = InsightPeriod.LAST_24_HOURS) -> PageInsights`
Get page-level engagement metrics.

**Parameters:**
- `period`: Time period (LAST_24_HOURS or LAST_7_DAYS)

**Returns:**
- PageInsights with page impressions, reach, engagement, fans, etc.

**Raises:**
- `FacebookAPIError`: If insights retrieval fails

##### Utility Methods

##### `verify_credentials() -> bool`
Verify that configured credentials are valid.

**Returns:**
- True if credentials are valid

**Raises:**
- `InvalidCredentialsError`: If credentials are invalid

##### `get_post(post_id: str) -> Dict[str, Any]`
Retrieve details about a specific post.

**Parameters:**
- `post_id`: The Facebook post ID

**Returns:**
- Dictionary with post data

### Models

#### TextPostRequest
```python
class TextPostRequest(BaseModel):
    message: str  # 1-63206 characters, cannot be empty/whitespace
```

#### ImagePostRequest
```python
class ImagePostRequest(BaseModel):
    message: Optional[str] = None  # Optional caption
    image_url: Optional[HttpUrl] = None  # URL to image
    image_path: Optional[str] = None  # Local file path
    
    # Either image_url OR image_path must be provided, not both
```

#### FacebookPostResponse
```python
class FacebookPostResponse(BaseModel):
    post_id: str  # ID of the created post
    success: bool = True  # Success status
    message: Optional[str] = None  # Additional info
```

### Exceptions

```python
from src.exceptions import (
    FacebookManagerError,      # Base exception
    FacebookAPIError,          # API-related errors
    InvalidCredentialsError,   # Authentication errors
    PostCreationError,         # Post creation failures
    ImageUploadError,          # Image upload failures
)
```

## 🧪 Testing

The project includes comprehensive unit and integration tests.

### Run All Tests

```bash
pytest tests/ -v
```

### Run Specific Test Suites

```bash
# Test models
pytest tests/test_models.py -v

# Test configuration
pytest tests/test_config.py -v

# Test Facebook Manager
pytest tests/test_facebook_manager.py -v
```

### Test Coverage

```bash
pytest --cov=src --cov-report=html tests/
```

## 📖 Examples

The `examples/` directory contains working examples:

- `example_text_post.py` - Simple text posting
- `example_image_post_url.py` - Image posting from URL
- `example_image_post_file.py` - Image posting from file
- `example_context_manager.py` - Using context manager pattern

Run any example:

```bash
python examples/example_text_post.py
```

## 🏗️ Project Structure

```
spec_drive_development/
├── .env                          # Environment variables (not in git)
├── README.md                     # This file
├── requirements.txt              # Python dependencies
│
├── src/                          # Main source code
│   ├── __init__.py              # Package exports
│   ├── config.py                # Configuration management
│   ├── models.py                # Pydantic models
│   ├── exceptions.py            # Custom exceptions
│   └── facebook_manager.py      # Core Facebook API client
│
├── tests/                        # Test suite
│   ├── __init__.py
│   ├── conftest.py              # Pytest configuration
│   ├── test_models.py           # Model tests
│   ├── test_config.py           # Config tests
│   └── test_facebook_manager.py # Integration tests
│
└── examples/                     # Usage examples
    ├── example_text_post.py
    ├── example_image_post_url.py
    ├── example_image_post_file.py
    └── example_context_manager.py
```

## 🔒 Security Best Practices

1. **Never commit credentials**: Keep `.env` out of version control
2. **Token rotation**: Regularly rotate your access tokens
3. **Minimal permissions**: Only request necessary Facebook permissions
4. **Environment-specific tokens**: Use different tokens for dev/staging/prod
5. **Validate inputs**: All inputs are validated via Pydantic models

## 🐛 Troubleshooting

### Common Issues

#### "Invalid OAuth access token"
- **Cause**: Token expired or invalid
- **Solution**: Generate a new access token from Facebook Developers

#### "Facebook Page ID must be numeric"
- **Cause**: Incorrect page ID format
- **Solution**: Ensure you're using the numeric page ID, not the username

#### "Image file not found"
- **Cause**: Invalid file path
- **Solution**: Use absolute paths or verify file exists

#### "Invalid image format"
- **Cause**: Unsupported file type
- **Solution**: Use supported formats: jpg, png, gif, bmp, webp

### Debug Mode

Enable detailed logging:

```python
import logging

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
```

## 🗺️ Roadmap

- [x] Text post creation
- [x] Image post creation (URL & file)
- [x] Comprehensive testing
- [x] Type-safe models
- [ ] Video post creation
- [ ] Comment monitoring
- [ ] Reaction tracking
- [ ] Post scheduling
- [ ] Analytics dashboard
- [ ] Webhook integration
- [ ] Multi-page management

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Add tests for new features
4. Ensure all tests pass
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License.

## 🙏 Acknowledgments

- Built for multi-agent systems integration
- Uses Facebook Graph API v18.0+
- Powered by Pydantic for data validation

## 📞 Support

For issues, questions, or contributions:
- Create an issue on GitHub
- Check existing documentation
- Review example scripts

---

**Built with ❤️ for the Agentic AI ecosystem**
