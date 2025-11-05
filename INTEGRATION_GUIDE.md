# Facebook Manager - Integration Guide

**Quick integration reference for multi-agent systems and external applications.**

---

## 🚀 Quick Start

### Installation
```bash
pip install -r requirements.txt
```

### Configuration
```python
# Set environment variables or create .env file
FACEBOOK_PAGE_ID=your_numeric_page_id
FACEBOOK_ACCESS_TOKEN=your_page_access_token
```

### Basic Usage
```python
from src import FacebookManager

with FacebookManager() as manager:
    # Your code here
    pass
```

---

## 📋 Available Tools/Functions

### 1. Content Publishing

#### 1.1 Create Text Post
**Function:** `create_text_post(post_request)`

**Arguments:**
- `post_request`: `TextPostRequest` object
  - `message` (str): Post content (1-63,206 characters)

**Returns:** `FacebookPostResponse`
- `post_id` (str): Created post ID
- `success` (bool): Operation status
- `message` (str, optional): Additional info

**Example:**
```python
from src import FacebookManager, TextPostRequest

manager = FacebookManager()
post = TextPostRequest(message="Hello, World!")
response = manager.create_text_post(post)
print(response.post_id)  # "123456789_987654321"
```

**Agent Integration:**
```json
{
  "tool": "create_text_post",
  "parameters": {
    "message": "Your post content here"
  }
}
```

---

#### 1.2 Create Image Post
**Function:** `create_image_post(post_request)`

**Arguments:**
- `post_request`: `ImagePostRequest` object
  - `message` (str, optional): Post caption
  - `image_url` (str, optional): URL to image (https://)
  - `image_path` (str, optional): Local file path
  - **Note:** Provide either `image_url` OR `image_path`, not both

**Returns:** `FacebookPostResponse` (same as 1.1)

**Example (URL):**
```python
from src import FacebookManager, ImagePostRequest

manager = FacebookManager()
post = ImagePostRequest(
    message="Check this out!",
    image_url="https://example.com/image.jpg"
)
response = manager.create_image_post(post)
```

**Example (File):**
```python
post = ImagePostRequest(
    message="Photo upload",
    image_path="/path/to/image.jpg"
)
response = manager.create_image_post(post)
```

**Agent Integration:**
```json
{
  "tool": "create_image_post",
  "parameters": {
    "message": "Optional caption",
    "image_url": "https://example.com/image.jpg"
  }
}
```

**Supported Formats:** JPG, PNG, GIF, BMP, WEBP

---

### 2. Comment Management

#### 2.1 Get Post Comments
**Function:** `get_post_comments(post_id, limit)`

**Arguments:**
- `post_id` (str): Facebook post ID (format: "pageID_postID")
- `limit` (int, optional): Max comments to retrieve (default: 100)

**Returns:** `CommentsResponse`
- `comments` (List[CommentData]): List of comments
  - `comment_id` (str): Unique comment identifier
  - `post_id` (str): Parent post ID
  - `message` (str): Comment text
  - `from_user` (dict): `{"id": str, "name": str}`
  - `created_time` (str): ISO 8601 timestamp
  - `like_count` (int): Number of likes
  - `comment_count` (int): Number of replies

**Example:**
```python
from src import FacebookManager

manager = FacebookManager()
comments = manager.get_post_comments(
    post_id="123456789_987654321",
    limit=50
)

for comment in comments.comments:
    print(f"{comment.from_user['name']}: {comment.message}")
```

**Agent Integration:**
```json
{
  "tool": "get_post_comments",
  "parameters": {
    "post_id": "123456789_987654321",
    "limit": 50
  }
}
```

---

#### 2.2 Extract Keywords from Comments
**Function:** `extract_keywords(comments, top_n)`

**Arguments:**
- `comments` (List[CommentData]): List of comment objects
- `top_n` (int, optional): Number of keywords to return (default: 10)

**Returns:** `List[Tuple[str, int]]`
- List of tuples: `(keyword, frequency)`
- Sorted by frequency (descending)

**Example:**
```python
manager = FacebookManager()
comments = manager.get_post_comments("123456789_987654321")
keywords = manager.extract_keywords(comments.comments, top_n=15)

for word, count in keywords:
    print(f"{word}: {count} mentions")
```

**Agent Integration:**
```json
{
  "tool": "analyze_comments",
  "parameters": {
    "post_id": "123456789_987654321",
    "top_keywords": 15
  }
}
```

**Note:** Uses frequency-based analysis with stop words filtering. No AI/ML required.

---

#### 2.3 Reply to Comment
**Function:** `reply_to_comment(request)`

**Arguments:**
- `request`: `CommentReplyRequest` object
  - `comment_id` (str): Comment ID to reply to
  - `message` (str): Reply message (1-8,000 characters)

**Returns:** `CommentActionResponse`
- `success` (bool): Operation status
- `comment_id` (str): Reply comment ID
- `message` (str): Status message

**Example:**
```python
from src import FacebookManager, CommentReplyRequest

manager = FacebookManager()
reply = CommentReplyRequest(
    comment_id="comment_123",
    message="Thank you for your feedback!"
)
response = manager.reply_to_comment(reply)
```

**Agent Integration:**
```json
{
  "tool": "reply_to_comment",
  "parameters": {
    "comment_id": "comment_123",
    "message": "Thank you for your feedback!"
  }
}
```

---

#### 2.4 React to Comment (Like)
**Function:** `react_to_comment(request)`

**Arguments:**
- `request`: `CommentReactionRequest` object
  - `comment_id` (str): Comment ID to react to

**Returns:** `CommentActionResponse` (same as 2.3)

**Example:**
```python
from src import FacebookManager, CommentReactionRequest

manager = FacebookManager()
reaction = CommentReactionRequest(comment_id="comment_123")
response = manager.react_to_comment(reaction)
```

**Agent Integration:**
```json
{
  "tool": "react_to_comment",
  "parameters": {
    "comment_id": "comment_123"
  }
}
```

---

#### 2.5 Hide Comment
**Function:** `hide_comment(comment_id)`

**Arguments:**
- `comment_id` (str): Comment ID to hide

**Returns:** `CommentActionResponse`
- `success` (bool): Operation status
- `is_hidden` (str): "true" if hidden
- `message` (str): Status message

**Example:**
```python
manager = FacebookManager()
response = manager.hide_comment("comment_123")
```

**Agent Integration:**
```json
{
  "tool": "hide_comment",
  "parameters": {
    "comment_id": "comment_123"
  }
}
```

**Note:** Comment remains visible to author and their friends.

---

#### 2.6 Delete Comment
**Function:** `delete_comment(comment_id)`

**Arguments:**
- `comment_id` (str): Comment ID to delete

**Returns:** `CommentActionResponse` (same as 2.5)

**Example:**
```python
manager = FacebookManager()
response = manager.delete_comment("comment_123")
```

**Agent Integration:**
```json
{
  "tool": "delete_comment",
  "parameters": {
    "comment_id": "comment_123"
  }
}
```

**⚠️ Warning:** Permanent deletion. Cannot be undone.

---

### 3. Analytics & Insights

#### 3.1 Get Post Insights
**Function:** `get_post_insights(post_id, period)`

**Arguments:**
- `post_id` (str): Facebook post ID
- `period` (InsightPeriod, optional): Time period
  - `InsightPeriod.LAST_24_HOURS` (default)
  - `InsightPeriod.LAST_7_DAYS`

**Returns:** `PostInsights`
- `post_id` (str): Post identifier
- `period` (str): "day" or "week"
- `reach` (int): Unique users reached
- `impressions` (int): Total views
- `reactions` (ReactionBreakdown): Reaction details
  - `like`, `love`, `wow`, `haha`, `sad`, `angry`, `care` (int)
  - `computed_total` (int): Sum of all reactions
- `comments_count` (int): Number of comments
- `shares_count` (int): Number of shares
- `clicked` (int): Post clicks
- `engagement_rate` (float): Computed engagement percentage

**Example:**
```python
from src import FacebookManager, InsightPeriod

manager = FacebookManager()
insights = manager.get_post_insights(
    post_id="123456789_987654321",
    period=InsightPeriod.LAST_24_HOURS
)

print(f"Reach: {insights.reach}")
print(f"Engagement Rate: {insights.engagement_rate}%")
print(f"Total Reactions: {insights.reactions.computed_total}")
```

**Agent Integration:**
```json
{
  "tool": "get_post_insights",
  "parameters": {
    "post_id": "123456789_987654321",
    "period": "day"
  }
}
```

**Period Values:**
- `"day"` = Last 24 hours
- `"week"` = Last 7 days

---

#### 3.2 Get Page Insights
**Function:** `get_page_insights(period)`

**Arguments:**
- `period` (InsightPeriod, optional): Time period (same as 3.1)

**Returns:** `PageInsights`
- `page_id` (str): Page identifier
- `period` (str): "day" or "week"
- `page_impressions` (int): Total page views
- `page_impressions_unique` (int): Unique page views
- `page_engaged_users` (int): Users who engaged
- `page_fans` (int): Total page likes
- `page_views_total` (int): Page tab views
- `page_consumptions` (int): Content clicks

**Example:**
```python
from src import FacebookManager, InsightPeriod

manager = FacebookManager()
insights = manager.get_page_insights(
    period=InsightPeriod.LAST_7_DAYS
)

print(f"Page Impressions: {insights.page_impressions}")
print(f"Engaged Users: {insights.page_engaged_users}")
```

**Agent Integration:**
```json
{
  "tool": "get_page_insights",
  "parameters": {
    "period": "week"
  }
}
```

---

### 4. Utility Functions

#### 4.1 Verify Credentials
**Function:** `verify_credentials()`

**Arguments:** None

**Returns:** `bool`
- `True` if credentials are valid
- Raises exception if invalid

**Example:**
```python
manager = FacebookManager()
if manager.verify_credentials():
    print("Credentials valid!")
```

---

#### 4.2 Get Post Details
**Function:** `get_post(post_id)`

**Arguments:**
- `post_id` (str): Facebook post ID

**Returns:** `Dict[str, Any]`
- Raw post data from Facebook API

**Example:**
```python
manager = FacebookManager()
post_data = manager.get_post("123456789_987654321")
print(post_data['permalink_url'])
```

---

## 🔧 Error Handling

### Exception Types

```python
from src.exceptions import (
    FacebookManagerError,      # Base exception
    FacebookAPIError,          # API errors
    InvalidCredentialsError,   # Auth errors
    PostCreationError,         # Post failures
    ImageUploadError           # Image failures
)
```

### Example Error Handling

```python
from src import FacebookManager
from src.exceptions import FacebookAPIError, InvalidCredentialsError

try:
    manager = FacebookManager()
    comments = manager.get_post_comments("post_id")
    
except InvalidCredentialsError as e:
    print(f"Auth failed: {e}")
    
except FacebookAPIError as e:
    print(f"API error: {e}")
    
except Exception as e:
    print(f"Unexpected error: {e}")
```

---

## 🎯 Agent Integration Patterns

### Pattern 1: Simple Function Call
```python
def agent_create_post(message: str) -> dict:
    """Agent wrapper for post creation"""
    manager = FacebookManager()
    request = TextPostRequest(message=message)
    response = manager.create_text_post(request)
    
    return {
        "success": True,
        "post_id": response.post_id
    }
```

### Pattern 2: Context Manager
```python
def agent_analyze_engagement(post_id: str) -> dict:
    """Agent wrapper for engagement analysis"""
    with FacebookManager() as manager:
        comments = manager.get_post_comments(post_id, limit=100)
        insights = manager.get_post_insights(post_id)
        keywords = manager.extract_keywords(comments.comments)
        
        return {
            "total_comments": len(comments.comments),
            "reach": insights.reach,
            "engagement_rate": insights.engagement_rate,
            "top_keywords": keywords[:5]
        }
```

### Pattern 3: Error-Safe Wrapper
```python
def agent_safe_action(action: str, **kwargs) -> dict:
    """Safe wrapper with error handling"""
    try:
        manager = FacebookManager()
        
        if action == "post":
            request = TextPostRequest(message=kwargs['message'])
            result = manager.create_text_post(request)
            return {"success": True, "data": result.model_dump()}
            
        elif action == "comments":
            result = manager.get_post_comments(kwargs['post_id'])
            return {"success": True, "data": [c.model_dump() for c in result.comments]}
            
    except Exception as e:
        return {"success": False, "error": str(e)}
```

---

## 📊 Data Format Reference

### JSON Output Example

```json
{
  "post_insights": {
    "post_id": "123456789_987654321",
    "period": "day",
    "reach": 1500,
    "impressions": 2300,
    "reactions": {
      "like": 45,
      "love": 12,
      "wow": 3,
      "haha": 5,
      "sad": 0,
      "angry": 0,
      "care": 2,
      "computed_total": 67
    },
    "comments_count": 23,
    "shares_count": 8,
    "clicked": 120,
    "engagement_rate": 4.26
  },
  "comments": [
    {
      "comment_id": "comment_123",
      "post_id": "123456789_987654321",
      "message": "Great post!",
      "from_user": {"id": "user_456", "name": "John Doe"},
      "created_time": "2025-11-05T10:30:00+0000",
      "like_count": 5,
      "comment_count": 2
    }
  ]
}
```

---

## ⚙️ Configuration

### Environment Variables

```bash
# Required
FACEBOOK_PAGE_ID=123456789           # Numeric page ID
FACEBOOK_ACCESS_TOKEN=EAAxxxxx...    # Page access token

# Optional
FACEBOOK_API_VERSION=v18.0           # Default: v18.0
REQUEST_TIMEOUT=30                   # Default: 30 seconds
MAX_RETRIES=3                        # Default: 3 retries
```

### Programmatic Configuration

```python
from src import FacebookConfig, FacebookManager

config = FacebookConfig(
    page_id="123456789",
    access_token="your_token",
    api_version="v18.0"
)

manager = FacebookManager(config=config)
```

---

## 🔒 Security Best Practices

1. **Never hardcode tokens** - Use environment variables
2. **Rotate tokens regularly** - Generate new tokens monthly
3. **Use minimal permissions** - Only request needed scopes:
   - `pages_manage_posts`
   - `pages_read_engagement`
   - `pages_manage_engagement`
4. **Validate all inputs** - Pydantic models handle this automatically
5. **Handle errors gracefully** - Don't expose token in error messages

---

## 📝 Testing Integration

### Mock Example

```python
from unittest.mock import Mock, patch
from src import FacebookManager, TextPostRequest

@patch('src.facebook_manager.requests.Session.request')
def test_integration(mock_request):
    # Mock API response
    mock_response = Mock()
    mock_response.json.return_value = {'id': '123_456'}
    mock_request.return_value = mock_response
    
    # Test your integration
    manager = FacebookManager()
    post = TextPostRequest(message="Test")
    response = manager.create_text_post(post)
    
    assert response.post_id == '123_456'
```

---

## 🚀 Performance Tips

1. **Reuse FacebookManager instance** - Reuses HTTP session
2. **Use context manager** - Ensures proper cleanup
3. **Batch operations** - Get multiple insights in one call when possible
4. **Limit pagination** - Only request comments you need
5. **Cache insights** - Facebook data updates every few minutes

---

## 📞 Quick Troubleshooting

| Error | Solution |
|-------|----------|
| Invalid OAuth token | Regenerate token from Facebook Developers |
| Page ID must be numeric | Use numeric ID, not username |
| Post not found | Verify post exists and is published |
| Permission denied | Check token has required scopes |
| Rate limit exceeded | Implement exponential backoff |

---

## 📚 Additional Resources

- **Full API Documentation:** [README.md](README.md)
- **Quick Reference:** [QUICK_REFERENCE.md](QUICK_REFERENCE.md)
- **Implementation Details:** [IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md)
- **Example Scripts:** `/examples/` directory
- **Facebook Graph API:** https://developers.facebook.com/docs/graph-api

---

**Last Updated:** November 2025  
**API Version:** Facebook Graph API v18.0  
**Python Version:** 3.8+
