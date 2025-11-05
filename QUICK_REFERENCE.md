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

### Create Text Post
```python
from src import FacebookManager, TextPostRequest

with FacebookManager() as manager:
    post = TextPostRequest(message="Your message here")
    response = manager.create_text_post(post)
    print(f"Post ID: {response.post_id}")
```

### Create Image Post (URL)
```python
from src import FacebookManager, ImagePostRequest

with FacebookManager() as manager:
    post = ImagePostRequest(
        message="Optional caption",
        image_url="https://example.com/image.jpg"
    )
    response = manager.create_image_post(post)
```

### Create Image Post (File)
```python
from src import FacebookManager, ImagePostRequest

with FacebookManager() as manager:
    post = ImagePostRequest(
        message="Optional caption",
        image_path="/path/to/image.jpg"
    )
    response = manager.create_image_post(post)
```

### Verify Credentials
```python
from src import FacebookManager

with FacebookManager() as manager:
    if manager.verify_credentials():
        print("Credentials are valid!")
```

### Get Post Details
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

### TextPostRequest
```python
TextPostRequest(
    message: str  # 1-63206 characters, required
)
```

### ImagePostRequest
```python
ImagePostRequest(
    message: Optional[str] = None,  # Optional caption
    image_url: Optional[HttpUrl] = None,  # OR
    image_path: Optional[str] = None  # Local file path
)
# Note: Provide either image_url OR image_path, not both
```

### FacebookPostResponse
```python
{
    "post_id": str,  # ID of created post
    "success": bool,  # Always True if returned
    "message": Optional[str]  # Additional info
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
  └── example_image_post_file.py
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

| Method | Description | Returns |
|--------|-------------|---------|
| `create_text_post(request)` | Create text post | FacebookPostResponse |
| `create_image_post(request)` | Create image post | FacebookPostResponse |
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
