# Facebook Manager - Quick Reference

## 🚀 One-Minute Setup

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Configure credentials in .env
FACEBOOK_PAGE_ID=your_page_id
FACEBOOK_ACCESS_TOKEN=your_token

# 3. Run a test
python examples/example_text_post.py
```

---

## 📝 Common Tasks

### Content Publishing

#### Create Text Post
```python
from src import FacebookManager, TextPostRequest

with FacebookManager() as manager:
    post = TextPostRequest(message="Your message here")
    response = manager.create_text_post(post)
    print(f"Post ID: {response.post_id}")
```

#### Create Image Post (URL)
```python
from src import FacebookManager, ImagePostRequest

with FacebookManager() as manager:
    post = ImagePostRequest(
        message="Optional caption",
        image_url="https://example.com/image.jpg"
    )
    response = manager.create_image_post(post)
```

#### Create Image Post (File)
```python
from src import FacebookManager, ImagePostRequest

with FacebookManager() as manager:
    post = ImagePostRequest(
        message="Optional caption",
        image_path="/path/to/image.jpg"
    )
    response = manager.create_image_post(post)
```

### Comment Management

#### Get Comments from Post
```python
from src import FacebookManager

with FacebookManager() as manager:
    # Get up to 50 comments
    comments = manager.get_post_comments("post_id", limit=50)
    
    for comment in comments.comments:
        print(f"{comment.from_user['name']}: {comment.message}")
```

#### Extract Keywords from Comments
```python
from src import FacebookManager

with FacebookManager() as manager:
    comments = manager.get_post_comments("post_id")
    keywords = manager.extract_keywords(comments.comments, top_n=10)
    
    for keyword, count in keywords:
        print(f"{keyword}: {count} mentions")
```

#### Reply to Comment
```python
from src import FacebookManager, CommentReplyRequest

with FacebookManager() as manager:
    reply = CommentReplyRequest(
        comment_id="comment_123",
        message="Thank you for your comment!"
    )
    response = manager.reply_to_comment(reply)
```

#### Like a Comment
```python
from src import FacebookManager, CommentReactionRequest

with FacebookManager() as manager:
    reaction = CommentReactionRequest(comment_id="comment_123")
    response = manager.react_to_comment(reaction)
```

#### Hide a Comment
```python
from src import FacebookManager

with FacebookManager() as manager:
    response = manager.hide_comment("comment_123")
    print(f"Hidden: {response.is_hidden}")
```

#### Delete a Comment
```python
from src import FacebookManager

with FacebookManager() as manager:
    response = manager.delete_comment("comment_123")
    print(f"Deleted: {response.success}")
```

### Analytics & Insights

#### Get Post Insights (24h)
```python
from src import FacebookManager, InsightPeriod

with FacebookManager() as manager:
    insights = manager.get_post_insights(
        post_id="post_id",
        period=InsightPeriod.LAST_24_HOURS
    )
    
    print(f"Reach: {insights.reach:,}")
    print(f"Impressions: {insights.impressions:,}")
    print(f"Total Reactions: {insights.reactions.computed_total:,}")
    print(f"Engagement Rate: {insights.engagement_rate:.2f}%")
```

#### Get Post Insights (7 days)
```python
from src import FacebookManager, InsightPeriod

with FacebookManager() as manager:
    insights = manager.get_post_insights(
        post_id="post_id",
        period=InsightPeriod.LAST_7_DAYS
    )
```

#### Get Page Insights
```python
from src import FacebookManager, InsightPeriod

with FacebookManager() as manager:
    page_insights = manager.get_page_insights(
        period=InsightPeriod.LAST_24_HOURS
    )
    
    print(f"Page Impressions: {page_insights.page_impressions:,}")
    print(f"Engaged Users: {page_insights.page_engaged_users:,}")
    print(f"Total Fans: {page_insights.page_fans:,}")
```

### Utility Methods

#### Verify Credentials
```python
from src import FacebookManager

with FacebookManager() as manager:
    if manager.verify_credentials():
        print("Credentials are valid!")
```

#### Get Post Details
```python
from src import FacebookManager

with FacebookManager() as manager:
    post_data = manager.get_post("post_id_here")
    print(post_data['permalink_url'])
```

---

## 🛠️ Error Handling

```python
from src import FacebookManager, TextPostRequest
from src.exceptions import (
    InvalidCredentialsError,
    PostCreationError,
    FacebookAPIError
)

try:
    with FacebookManager() as manager:
        post = TextPostRequest(message="Test")
        manager.create_text_post(post)
        
except InvalidCredentialsError:
    print("Invalid Facebook credentials")
    
except PostCreationError as e:
    print(f"Failed to create post: {e}")
    
except FacebookAPIError as e:
    print(f"API error: {e}")
```

---

## 📦 Available Models

### Content Publishing Models

#### TextPostRequest
```python
TextPostRequest(
    message: str  # 1-63206 characters, required
)
```

#### ImagePostRequest
```python
ImagePostRequest(
    message: Optional[str] = None,  # Optional caption
    image_url: Optional[HttpUrl] = None,  # OR
    image_path: Optional[str] = None  # Local file path
)
# Note: Provide either image_url OR image_path, not both
```

#### FacebookPostResponse
```python
{
    "post_id": str,  # ID of created post
    "success": bool,  # Always True if returned
    "message": Optional[str]  # Additional info
}
```

### Comment Management Models

#### CommentData
```python
{
    "comment_id": str,
    "post_id": str,
    "message": str,
    "from_user": {"id": str, "name": str},
    "created_time": str,
    "like_count": int,
    "comment_count": int
}
```

#### CommentReplyRequest
```python
CommentReplyRequest(
    comment_id: str,
    message: str  # 1-8000 characters
)
```

#### CommentReactionRequest
```python
CommentReactionRequest(
    comment_id: str
)
```

#### CommentActionResponse
```python
{
    "success": bool,
    "comment_id": Optional[str],
    "message": str,
    "is_hidden": Optional[str]  # "true" or None
}
```

### Analytics Models

#### InsightPeriod (Enum)
```python
InsightPeriod.LAST_24_HOURS  # 24-hour metrics
InsightPeriod.LAST_7_DAYS    # 7-day metrics
```

#### PostInsights
```python
{
    "post_id": str,
    "period": str,
    "reach": int,
    "impressions": int,
    "reactions": ReactionBreakdown,
    "comments_count": int,
    "shares_count": int,
    "clicked": int,
    "engagement_rate": float  # Computed property
}
```

#### ReactionBreakdown
```python
{
    "like": int,    # 👍
    "love": int,    # ❤️
    "wow": int,     # 😮
    "haha": int,    # 😂
    "sad": int,     # 😢
    "angry": int,   # 😠
    "care": int,    # 🤗
    "computed_total": int  # Sum of all reactions
}
```

#### PageInsights
```python
{
    "page_id": str,
    "period": str,
    "page_impressions": int,
    "page_impressions_unique": int,
    "page_engaged_users": int,
    "page_fans": int,
    "page_views_total": int,
    "page_consumptions": int
}
```

---

## 🧪 Testing

```bash
# Run all unit tests
pytest tests/ -v

# Run specific test file
pytest tests/test_models.py -v

# Run with coverage
pytest --cov=src tests/

# Run real API integration test
python tests/test_real_integration.py
```

---

## 📁 File Structure

```
src/
  ├── facebook_manager.py  # Main API client
  ├── models.py           # Data models
  ├── config.py           # Configuration
  └── exceptions.py       # Custom exceptions

tests/
  ├── test_models.py      # Model tests
  ├── test_config.py      # Config tests
  └── test_facebook_manager.py  # API tests

examples/
  ├── example_text_post.py
  ├── example_image_post_url.py
  ├── example_image_post_file.py
  ├── example_context_manager.py
  ├── example_comment_management.py
  ├── example_post_insights.py
  └── example_page_insights.py
```

---

## ⚙️ Configuration Options

Environment variables in `.env`:

```bash
# Required
FACEBOOK_PAGE_ID=123456789
FACEBOOK_ACCESS_TOKEN=EAAxxxxx...

# Optional (with defaults)
FACEBOOK_API_VERSION=v18.0
FACEBOOK_API_BASE_URL=https://graph.facebook.com
REQUEST_TIMEOUT=30
MAX_RETRIES=3
```

---

## 🐛 Common Issues

### "Invalid OAuth access token"
**Solution**: Generate a new access token from Facebook Developers

### "Facebook Page ID must be numeric"
**Solution**: Use the numeric page ID, not the username

### "Image file not found"
**Solution**: Use absolute paths for image files

### "Invalid image format"
**Solution**: Use supported formats: jpg, png, gif, bmp, webp

---

## 📚 API Methods

### Content Publishing

| Method | Description | Returns |
|--------|-------------|---------|
| `create_text_post(request)` | Create text post | FacebookPostResponse |
| `create_image_post(request)` | Create image post | FacebookPostResponse |

### Comment Management

| Method | Description | Returns |
|--------|-------------|---------|
| `get_post_comments(post_id, limit)` | Get comments from post | CommentsResponse |
| `extract_keywords(comments, top_n)` | Extract keywords from comments | List[Tuple[str, int]] |
| `reply_to_comment(request)` | Reply to comment | CommentActionResponse |
| `react_to_comment(request)` | Like a comment | CommentActionResponse |
| `hide_comment(comment_id)` | Hide comment | CommentActionResponse |
| `delete_comment(comment_id)` | Delete comment | CommentActionResponse |

### Analytics & Insights

| Method | Description | Returns |
|--------|-------------|---------|
| `get_post_insights(post_id, period)` | Get post metrics | PostInsights |
| `get_page_insights(period)` | Get page metrics | PageInsights |

### Utility Methods

| Method | Description | Returns |
|--------|-------------|---------|
| `verify_credentials()` | Verify API credentials | bool |
| `get_post(post_id)` | Get post details | dict |
| `close()` | Close HTTP session | None |

---

## 🔗 Useful Links

- [Facebook Graph API Docs](https://developers.facebook.com/docs/graph-api)
- [Pydantic Documentation](https://docs.pydantic.dev/)
- [Project README](README.md)
- [Implementation Summary](IMPLEMENTATION_SUMMARY.md)

---

## 💡 Pro Tips

1. **Always use context manager**: `with FacebookManager() as manager:`
2. **Validate inputs**: Pydantic handles this automatically
3. **Handle errors gracefully**: Use specific exception types
4. **Test with mocks first**: Use `test_facebook_manager.py` as reference
5. **Keep tokens secure**: Never commit `.env` to git

---

**Need help? Check the [README.md](README.md) for detailed documentation!**