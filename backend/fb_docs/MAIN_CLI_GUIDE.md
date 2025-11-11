# Facebook Manager CLI Guide (`main.py`)

## Overview

The `main.py` script provides a command-line interface to interact with your Facebook Page using the Facebook Graph API. All commands work with **live data** from your Facebook Page.

## Prerequisites

Before using any command, ensure:

1. **Valid Facebook Credentials**: Your `.env` file must contain:
   - `FACEBOOK_PAGE_ID` - Your Facebook Page ID
   - `FACEBOOK_ACCESS_TOKEN` - A valid, non-expired Page Access Token

2. **Token Expiration**: Facebook access tokens expire. If you see "Session has expired" errors, you need to generate a new token from the [Facebook Graph API Explorer](https://developers.facebook.com/tools/explorer/).

## Commands

### 1. Verify Credentials

Check if your Facebook credentials are valid:

```bash
python main.py verify
```

**Expected output (success):**
```
Credentials verified successfully.
```

**Expected output (failure):**
```
Invalid credentials: Facebook API Error [190]: Error validating access token...
```

### 2. Fetch Post Comments & Insights

Retrieve comments and engagement insights for a specific Facebook post:

```bash
python main.py fetch-post-engagement <POST_ID> [OPTIONS]
```

**Required argument:**
- `POST_ID` - The post identifier in `PageID_PostID` format (e.g., `837535619434131_122113814331036166`)

**Options:**
- `--limit LIMIT` - Maximum number of comments to retrieve (default: 100)
- `--period PERIOD` - Insight period: `day`, `week`, `days_28`, or `lifetime` (default: day)
- `--output FILE` - Output file path (default: `last_post_engagement.json`). Use `-` for stdout.
- `--skip-output` - Don't write JSON output, just print summary

**Examples:**

```bash
# Fetch comments and insights for a post (saves to last_post_engagement.json)
python main.py fetch-post-engagement 837535619434131_122113814331036166

# Fetch up to 50 comments with lifetime insights
python main.py fetch-post-engagement 837535619434131_122113814331036166 --limit 50 --period lifetime

# Output to a custom file
python main.py fetch-post-engagement 837535619434131_122113814331036166 --output my_analysis.json

# Print JSON to console instead of file
python main.py fetch-post-engagement 837535619434131_122113814331036166 --output -

# Just show summary without saving
python main.py fetch-post-engagement 837535619434131_122113814331036166 --skip-output
```

**Output includes:**
- Comment count, reactions breakdown, reach, impressions
- Engagement rate
- First 5 comments preview
- Full JSON with all comments and insights metrics

**Finding Your Post ID:**

1. **From Facebook URL:**
   - Go to your post on Facebook
   - URL format: `https://www.facebook.com/YOUR_PAGE/posts/POST_ID`
   - The post ID is the number after `/posts/`
   - Combine with your page ID: `YOUR_PAGE_ID_POST_ID`

2. **From previous posts:**
   - Check the `post_id` field from posts you created via this tool
   - Already in the correct format

### 3. Post Text

Publish a text-only post to your Facebook Page:

```bash
python main.py post-text "Your message here"
```

**Examples:**

```bash
# Simple text post
python main.py post-text "Hello from the CLI! 🚀"

# Read from stdin (interactive)
python main.py post-text

# Read from stdin (pipe)
echo "Automated post content" | python main.py post-text
```

**Output:**
```
Post created successfully: 837535619434131_123456789012345
```

### 4. Post Image

Publish an image post to your Facebook Page:

```bash
python main.py post-image --image-url URL [--message "Caption"]
python main.py post-image --image-path PATH [--message "Caption"]
```

**Examples:**

```bash
# Post image from URL with message
python main.py post-image --image-url https://example.com/photo.jpg --message "Check this out!"

# Post image from local file
python main.py post-image --image-path ./images/photo.jpg --message "New product launch"

# Post image without caption
python main.py post-image --image-url https://picsum.photos/800/600
```

**Supported image formats:** JPG, PNG, GIF

### 5. Page Insights

Fetch page-level engagement metrics:

```bash
python main.py page-insights [--period PERIOD]
```

**Examples:**

```bash
# Get 24-hour page insights
python main.py page-insights

# Get 7-day insights
python main.py page-insights --period week

# Get 28-day insights
python main.py page-insights --period days_28
```

**Output includes:**
- Page impressions and reach
- Engaged users
- Post engagements
- Total fans
- Page views
- Content consumptions

## Common Issues & Solutions

### Issue: "Session has expired"

**Problem:** Your Facebook access token has expired.

**Solution:**
1. Go to [Facebook Graph API Explorer](https://developers.facebook.com/tools/explorer/)
2. Select your app and page
3. Generate a new Page Access Token with required permissions:
   - `pages_manage_posts`
   - `pages_read_engagement`
   - `pages_manage_engagement`
4. Update `FACEBOOK_ACCESS_TOKEN` in your `.env` file

### Issue: "Post ID not found" or "Invalid parameter"

**Problem:** Incorrect post ID format.

**Solution:** 
- Post ID must be in `PageID_PostID` format
- Example: `837535619434131_122113814331036166`
- Not just the post number alone

### Issue: "Configuration is invalid"

**Problem:** Missing or invalid environment variables.

**Solution:**
- Ensure `.env` file exists in the project root
- Check that `FACEBOOK_PAGE_ID` and `FACEBOOK_ACCESS_TOKEN` are set
- Page ID should be numeric only
- Access token should be long (100+ characters)

### Issue: "No comments found"

**Problem:** The post has no comments or you don't have permission.

**Solution:**
- Verify the post exists and is published
- Ensure your token has `pages_read_engagement` permission
- Check that the post is on the correct page

## Advanced Usage

### Custom Environment File

Use a different `.env` file:

```bash
python main.py --env-file /path/to/custom.env verify
```

### Use Environment Variables Only

Skip `.env` file loading:

```bash
export FACEBOOK_PAGE_ID="123456789"
export FACEBOOK_ACCESS_TOKEN="EAAxxxxx..."
python main.py --no-env-file verify
```

### Batch Processing

Fetch engagement for multiple posts:

```bash
# Using a bash script
for post_id in 837535619434131_111111111 837535619434131_222222222; do
    python main.py fetch-post-engagement "$post_id" --output "engagement_${post_id##*_}.json"
done
```

### JSON Output Processing

Process output with `jq`:

```bash
# Get just the comment count
python main.py fetch-post-engagement POST_ID --output - | jq '.comments_total'

# Extract all comment messages
python main.py fetch-post-engagement POST_ID --output - | jq '.comments[].message'

# Get engagement rate
python main.py fetch-post-engagement POST_ID --output - | jq '.insights.engagement_rate'
```

## Exit Codes

The script uses exit codes to indicate success/failure:

- `0` - Success
- `1` - General error (invalid arguments, file not found)
- `2` - Configuration validation error
- `3` - Invalid credentials
- `4` - Facebook API error
- `5` - Post creation or image upload error
- `6` - Input validation error
- `130` - User cancelled (Ctrl+C)

**Example usage in scripts:**

```bash
#!/bin/bash
python main.py verify
if [ $? -eq 0 ]; then
    echo "Credentials valid, proceeding..."
    python main.py post-text "Automated post"
else
    echo "Credentials invalid, exiting"
    exit 1
fi
```

## Full Command Reference

```bash
# Help
python main.py --help
python main.py <command> --help

# Verify credentials
python main.py verify [--quiet]

# Fetch post engagement
python main.py fetch-post-engagement POST_ID [--limit N] [--period PERIOD] [--output FILE] [--skip-output]

# Post text
python main.py post-text [MESSAGE]

# Post image
python main.py post-image (--image-url URL | --image-path PATH) [--message TEXT]

# Page insights
python main.py page-insights [--period PERIOD]
```

## Getting Help

For detailed help on any command:

```bash
python main.py <command> --help
```

For issues with the Facebook API, consult the [Facebook Graph API Documentation](https://developers.facebook.com/docs/graph-api/).