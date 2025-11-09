# Facebook Manager MCP Server

## Overview

This Model Context Protocol (MCP) server exposes the Facebook Manager toolkit as standardized tools that can be integrated with any MCP-compatible system (Claude Desktop, IDEs, AI agents, etc.).

## What is MCP?

The Model Context Protocol (MCP) is an open protocol that standardizes how applications provide context to AI models. It allows AI assistants to securely access data and tools from your systems.

**Learn more:** [https://modelcontextprotocol.io/](https://modelcontextprotocol.io/)

## Features

The Facebook Manager MCP server provides **11 tools** for complete Facebook Page management:

### Content Publishing
- 📝 **post_text_to_facebook** - Publish text posts
- 🖼️ **post_image_to_facebook** - Publish image posts with optional captions

### Engagement & Analytics
- 💬 **fetch_post_comments** - Retrieve comments with keyword extraction
- 📊 **fetch_post_insights** - Get post metrics (reach, impressions, reactions, etc.)
- 📈 **fetch_page_insights** - Get page-level engagement metrics

### Comment Management
- ↩️ **reply_to_comment** - Reply to comments as the page
- 👍 **like_comment** - Like comments to show engagement
- 🙈 **hide_comment** - Hide inappropriate comments
- 🗑️ **delete_comment** - Permanently remove comments

### Analysis
- 🔍 **extract_comment_keywords** - Analyze trending topics in comments

### Utilities
- ✅ **verify_facebook_credentials** - Test API connectivity

## Installation

### 1. Install Dependencies

```bash
# Install the MCP SDK
pip install mcp

# Or install all requirements
pip install -r requirements.txt
```

### 2. Configure Credentials

Create or update your `.env` file:

```env
FACEBOOK_PAGE_ID=your_page_id_here
FACEBOOK_ACCESS_TOKEN=your_access_token_here
FACEBOOK_API_VERSION=v18.0
```

**Get your credentials:**
1. Go to [Facebook Graph API Explorer](https://developers.facebook.com/tools/explorer/)
2. Select your app and page
3. Request permissions: `pages_manage_posts`, `pages_read_engagement`, `pages_manage_engagement`
4. Generate Page Access Token

### 3. Test the Server

```bash
# Run the MCP server directly
python mcp_server.py
```

The server will start and listen for MCP requests via stdio.

## Integration with MCP Clients

### Claude Desktop

Add to your Claude Desktop configuration (`%APPDATA%\Claude\claude_desktop_config.json` on Windows or `~/Library/Application Support/Claude/claude_desktop_config.json` on macOS):

```json
{
  "mcpServers": {
    "facebook-manager": {
      "command": "python",
      "args": [
        "d:\\spec_drive_development\\mcp_server.py"
      ],
      "env": {
        "FACEBOOK_PAGE_ID": "your_page_id_here",
        "FACEBOOK_ACCESS_TOKEN": "your_access_token_here"
      }
    }
  }
}
```

**Or use the .env file approach:**

```json
{
  "mcpServers": {
    "facebook-manager": {
      "command": "python",
      "args": [
        "d:\\spec_drive_development\\mcp_server.py"
      ]
    }
  }
}
```

(Server will automatically load `.env` from the project directory)

### Cline (VS Code Extension)

Add to Cline's MCP settings:

```json
{
  "mcpServers": {
    "facebook-manager": {
      "command": "python",
      "args": ["d:\\spec_drive_development\\mcp_server.py"]
    }
  }
}
```

### Other MCP Clients

Any MCP-compatible client can connect using the stdio transport:

```bash
python mcp_server.py
```

## Available Tools

### 1. verify_facebook_credentials

Verify that Facebook credentials are valid and working.

**Parameters:** None

**Example Response:**
```json
{
  "success": true,
  "message": "Facebook credentials verified successfully",
  "page_id": "123456789",
  "api_version": "v18.0"
}
```

### 2. post_text_to_facebook

Publish a text-only post to your Facebook Page.

**Parameters:**
- `message` (string, required): Text content (1-63206 characters)

**Example:**
```json
{
  "message": "Hello from the MCP server! 🚀"
}
```

**Response:**
```json
{
  "success": true,
  "post_id": "123456789_987654321",
  "message": "Text post published successfully"
}
```

### 3. post_image_to_facebook

Publish an image post with optional caption.

**Parameters:**
- `image_url` (string, optional): Public URL of the image
- `image_path` (string, optional): Local filesystem path to image
- `message` (string, optional): Caption text

**Note:** Provide either `image_url` OR `image_path`, not both.

**Example:**
```json
{
  "image_url": "https://example.com/photo.jpg",
  "message": "Check out our new product! 🎉"
}
```

**Response:**
```json
{
  "success": true,
  "post_id": "123456789_987654321",
  "message": "Image post published successfully"
}
```

### 4. fetch_post_comments

Retrieve comments from a specific post.

**Parameters:**
- `post_id` (string, required): Facebook post ID (format: PageID_PostID)
- `limit` (integer, optional): Max comments to retrieve (default: 100, max: 500)
- `extract_keywords` (boolean, optional): Extract trending keywords (default: true)

**Example:**
```json
{
  "post_id": "123456789_987654321",
  "limit": 50,
  "extract_keywords": true
}
```

**Response:**
```json
{
  "success": true,
  "post_id": "123456789_987654321",
  "total_comments": 42,
  "comments_retrieved": 42,
  "comments": [
    {
      "comment_id": "comment_123",
      "author": {
        "id": "user_123",
        "name": "John Doe"
      },
      "message": "Great post!",
      "created_time": "2025-11-05T10:00:00+0000",
      "like_count": 5,
      "reply_count": 2,
      "is_hidden": false
    }
  ],
  "keywords": [
    {"keyword": "great", "frequency": 10},
    {"keyword": "love", "frequency": 8}
  ],
  "has_more": false
}
```

### 5. fetch_post_insights

Get engagement metrics for a specific post.

**Parameters:**
- `post_id` (string, required): Facebook post ID
- `period` (string, optional): Time period - "day", "week", "days_28", or "lifetime" (default: "lifetime")

**Example:**
```json
{
  "post_id": "123456789_987654321",
  "period": "lifetime"
}
```

**Response:**
```json
{
  "success": true,
  "post_id": "123456789_987654321",
  "period": "lifetime",
  "reach": 1500,
  "impressions": 2000,
  "reactions": {
    "like": 50,
    "love": 30,
    "wow": 10,
    "haha": 5,
    "sad": 2,
    "angry": 1,
    "care": 2,
    "total": 100
  },
  "comments_count": 25,
  "shares_count": 10,
  "clicked": 75,
  "engagement_rate": 13.33
}
```

### 6. fetch_page_insights

Get page-level engagement metrics.

**Parameters:**
- `period` (string, optional): "day", "week", or "days_28" (default: "day")

**Example:**
```json
{
  "period": "week"
}
```

**Response:**
```json
{
  "success": true,
  "page_id": "123456789",
  "period": "week",
  "page_impressions": 5000,
  "page_reach": 3500,
  "page_engaged_users": 500,
  "page_post_engagements": 350,
  "page_fans": 10000,
  "page_fans_online": 450,
  "page_views_total": 1200,
  "page_consumptions": 800
}
```

### 7. reply_to_comment

Reply to a comment as the Facebook Page.

**Parameters:**
- `comment_id` (string, required): Facebook comment ID
- `message` (string, required): Reply message (1-8000 characters)

**Example:**
```json
{
  "comment_id": "comment_123",
  "message": "Thank you for your feedback! 😊"
}
```

**Response:**
```json
{
  "success": true,
  "comment_id": "comment_123",
  "action": "reply",
  "message": "Reply posted successfully"
}
```

### 8. like_comment

Like a comment as the Facebook Page.

**Parameters:**
- `comment_id` (string, required): Facebook comment ID

**Example:**
```json
{
  "comment_id": "comment_123"
}
```

**Response:**
```json
{
  "success": true,
  "comment_id": "comment_123",
  "action": "like",
  "message": "Comment liked successfully"
}
```

### 9. hide_comment

Hide a comment from public view.

**Parameters:**
- `comment_id` (string, required): Facebook comment ID

**Example:**
```json
{
  "comment_id": "comment_123"
}
```

**Response:**
```json
{
  "success": true,
  "comment_id": "comment_123",
  "action": "hide",
  "message": "Comment hidden successfully"
}
```

### 10. delete_comment

Permanently delete a comment.

**Parameters:**
- `comment_id` (string, required): Facebook comment ID

**Example:**
```json
{
  "comment_id": "comment_123"
}
```

**Response:**
```json
{
  "success": true,
  "comment_id": "comment_123",
  "action": "delete",
  "message": "Comment deleted successfully"
}
```

### 11. extract_comment_keywords

Analyze and extract trending keywords from post comments.

**Parameters:**
- `post_id` (string, required): Facebook post ID
- `top_n` (integer, optional): Number of top keywords (default: 20, max: 100)
- `min_length` (integer, optional): Minimum word length (default: 3)

**Example:**
```json
{
  "post_id": "123456789_987654321",
  "top_n": 10,
  "min_length": 4
}
```

**Response:**
```json
{
  "success": true,
  "post_id": "123456789_987654321",
  "total_comments_analyzed": 150,
  "keywords": [
    {"keyword": "product", "frequency": 25},
    {"keyword": "amazing", "frequency": 20},
    {"keyword": "quality", "frequency": 18}
  ]
}
```

## Usage Examples

### With Claude Desktop

Once configured, you can ask Claude to:

```
"Post 'Happy Monday everyone!' to my Facebook page"

"Fetch all comments from post ID 123456789_987654321 and analyze sentiment"

"Show me engagement metrics for my last post"

"Reply to comment comment_456 with 'Thank you for the feedback!'"

"Get my page insights for the past week"
```

### Programmatic Usage (Python)

```python
import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def main():
    server_params = StdioServerParameters(
        command="python",
        args=["mcp_server.py"],
    )
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            # List available tools
            tools = await session.list_tools()
            print(f"Available tools: {[t.name for t in tools.tools]}")
            
            # Verify credentials
            result = await session.call_tool(
                "verify_facebook_credentials",
                arguments={}
            )
            print(result.content)
            
            # Post a message
            result = await session.call_tool(
                "post_text_to_facebook",
                arguments={"message": "Hello from MCP!"}
            )
            print(result.content)

if __name__ == "__main__":
    asyncio.run(main())
```

## Error Handling

All tools return JSON responses with a `success` field:

**Success:**
```json
{
  "success": true,
  "...": "additional data"
}
```

**Failure:**
```json
{
  "success": false,
  "error": "Error type",
  "message": "Detailed error message"
}
```

**Common Error Types:**
- `"Invalid credentials"` - Access token expired or invalid
- `"Facebook API error"` - Facebook API returned an error
- `"Validation error"` - Invalid input parameters
- `"Post creation failed"` - Could not create the post
- `"Image post failed"` - Image upload or posting failed

## Troubleshooting

### Server Won't Start

**Issue:** "Failed to initialize server"

**Solution:**
1. Check `.env` file exists and has valid credentials
2. Run `python diagnose.py` to identify configuration issues
3. Verify Python version is 3.8+
4. Ensure all dependencies are installed: `pip install -r requirements.txt`

### Token Expired

**Issue:** "Session has expired" or error code 190

**Solution:**
1. Visit [Facebook Graph API Explorer](https://developers.facebook.com/tools/explorer/)
2. Generate a new Page Access Token
3. Update `FACEBOOK_ACCESS_TOKEN` in `.env`
4. Restart the MCP server

### Tool Not Found

**Issue:** MCP client can't see the tools

**Solution:**
1. Restart your MCP client (Claude Desktop, etc.)
2. Check the server is running: look for logs
3. Verify the configuration path in your MCP client config
4. Ensure the Python path and script path are correct

### Permission Errors

**Issue:** "Insufficient permissions" errors

**Solution:**
1. Regenerate your access token with required permissions:
   - `pages_manage_posts`
   - `pages_read_engagement`
   - `pages_manage_engagement`
2. Ensure you're using a **Page Access Token**, not a User Access Token

## Security Best Practices

1. **Never commit `.env` files** - Keep credentials out of version control
2. **Use environment variables** - Prefer env vars over config files in production
3. **Rotate tokens regularly** - Generate new access tokens periodically
4. **Limit permissions** - Only request necessary Facebook permissions
5. **Monitor usage** - Check Facebook's API logs for unusual activity

## Advanced Configuration

### Custom Logging

Set logging level via environment variable:

```bash
export LOG_LEVEL=DEBUG
python mcp_server.py
```

Or in your MCP client config:

```json
{
  "mcpServers": {
    "facebook-manager": {
      "command": "python",
      "args": ["mcp_server.py"],
      "env": {
        "LOG_LEVEL": "DEBUG"
      }
    }
  }
}
```

### Multiple Page Support

To manage multiple Facebook Pages, create separate server instances:

```json
{
  "mcpServers": {
    "facebook-page-1": {
      "command": "python",
      "args": ["mcp_server.py"],
      "env": {
        "FACEBOOK_PAGE_ID": "page1_id",
        "FACEBOOK_ACCESS_TOKEN": "page1_token"
      }
    },
    "facebook-page-2": {
      "command": "python",
      "args": ["mcp_server.py"],
      "env": {
        "FACEBOOK_PAGE_ID": "page2_id",
        "FACEBOOK_ACCESS_TOKEN": "page2_token"
      }
    }
  }
}
```

## Resources

- **MCP Documentation:** [https://modelcontextprotocol.io/](https://modelcontextprotocol.io/)
- **Facebook Graph API:** [https://developers.facebook.com/docs/graph-api/](https://developers.facebook.com/docs/graph-api/)
- **Claude Desktop:** [https://claude.ai/download](https://claude.ai/download)
- **Project Repository:** [Your GitHub URL]

## Support

For issues or questions:
1. Run `python diagnose.py` to check your setup
2. Check the logs for error details
3. Consult the Facebook Graph API documentation
4. Review this guide for troubleshooting steps

## License

[Your License Here]
