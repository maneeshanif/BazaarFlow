# API Reference - Google Drive MCP Integration

## Table of Contents

1. [MCP Client API](#mcp-client-api)
2. [Google Drive Tools API](#google-drive-tools-api)
3. [Agent API](#agent-api)
4. [Data Models](#data-models)
5. [Error Handling](#error-handling)

---

## MCP Client API

### `GDriveMCPClient`

Low-level client for communicating with the Google Drive MCP server.

#### Constructor

```python
GDriveMCPClient(credentials_path: Optional[str] = None)
```

**Parameters:**
- `credentials_path` (str, optional): Path to `.gdrive-server-credentials.json`. Defaults to environment variable `GDRIVE_CREDENTIALS_PATH` or `.gdrive-server-credentials.json`.

**Example:**
```python
from tools.gdrive_mcp_client import GDriveMCPClient

client = GDriveMCPClient("/path/to/credentials.json")
```

#### Methods

##### `async start()`

Starts the MCP server process.

**Returns:** None

**Raises:**
- `RuntimeError`: If npx is not found

**Example:**
```python
await client.start()
```

##### `async stop()`

Stops the MCP server process.

**Returns:** None

**Example:**
```python
await client.stop()
```

##### `async list_resources(cursor: Optional[str] = None)`

Lists Google Drive files with pagination.

**Parameters:**
- `cursor` (str, optional): Pagination cursor for next page

**Returns:** `Dict[str, Any]`
```python
{
    "resources": [
        {
            "uri": "gdrive:///file_id",
            "name": "Document.docx",
            "mimeType": "application/vnd.google-apps.document"
        },
        # ... more files
    ],
    "nextCursor": "next_page_token"  # or None
}
```

**Example:**
```python
result = await client.list_resources()
for resource in result["resources"]:
    print(resource["name"])
```

##### `async read_resource(uri: str)`

Reads the content of a specific file.

**Parameters:**
- `uri` (str): Resource URI in format `gdrive:///file_id`

**Returns:** `Dict[str, Any]`
```python
{
    "contents": [
        {
            "uri": "gdrive:///file_id",
            "mimeType": "text/markdown",
            "text": "# File content..."  # For text files
            # or
            "blob": "base64_encoded_data"  # For binary files
        }
    ]
}
```

**Example:**
```python
content = await client.read_resource("gdrive:///1ABC123XYZ")
print(content["contents"][0]["text"])
```

##### `async search_files(query: str)`

Searches for files in Google Drive.

**Parameters:**
- `query` (str): Search query string

**Returns:** `Dict[str, Any]`
```python
{
    "content": [
        {
            "type": "text",
            "text": "Found 3 files:\nReport.docx (application/vnd...)\n..."
        }
    ],
    "isError": False
}
```

**Example:**
```python
results = await client.search_files("budget report")
print(results["content"][0]["text"])
```

##### `async list_tools()`

Lists available tools from the MCP server.

**Returns:** `List[Dict[str, Any]]`

**Example:**
```python
tools = await client.list_tools()
for tool in tools:
    print(f"Tool: {tool['name']}")
```

### Context Manager

```python
async with get_gdrive_client(credentials_path: Optional[str] = None) as client:
    # Use client
    results = await client.search_files("query")
```

**Example:**
```python
from tools.gdrive_mcp_client import get_gdrive_client

async with get_gdrive_client() as client:
    results = await client.search_files("reports")
    print(results)
```

---

## Google Drive Tools API

High-level functions for agent integration.

### `search_gdrive_files(query: str)`

Search for files in Google Drive.

**Parameters:**
- `query` (str): Search query

**Returns:** `FileSearchResult`

**Example:**
```python
from tools.gdrive_tools import search_gdrive_files

result = await search_gdrive_files("quarterly report")
print(f"Found {result.files_found} files")
print(result.file_list)
```

### `read_gdrive_file(file_id: str)`

Read a specific file from Google Drive.

**Parameters:**
- `file_id` (str): Google Drive file ID

**Returns:** `FileContent`

**Raises:**
- `Exception`: If file not found or access denied

**Example:**
```python
from tools.gdrive_tools import read_gdrive_file

content = await read_gdrive_file("1ABC123XYZ")
if content.is_text:
    print(content.content)
else:
    print(f"Binary file: {content.mime_type}")
```

### `list_gdrive_files(cursor: Optional[str] = None)`

List files from Google Drive.

**Parameters:**
- `cursor` (str, optional): Pagination cursor

**Returns:** `FileListResult`

**Example:**
```python
from tools.gdrive_tools import list_gdrive_files

result = await list_gdrive_files()
for file in result.files:
    print(f"{file['name']} - {file['mimeType']}")

# Get next page
if result.has_more:
    next_page = await list_gdrive_files(result.next_cursor)
```

### Tool Functions (for Agent)

These are the function tool wrappers used by the agent.

#### `tool_search_gdrive(query: str)`

**Returns:** `dict`
```python
{
    "success": True,
    "files_found": 3,
    "files": "Report.docx\nBudget.xlsx\n...",
    "query": "reports"
}
```

#### `tool_read_gdrive_file(file_id: str)`

**Returns:** `dict`
```python
{
    "success": True,
    "file_id": "1ABC123",
    "mime_type": "text/markdown",
    "content": "# File content...",
    "is_text": True
}
```

#### `tool_list_gdrive_files()`

**Returns:** `dict`
```python
{
    "success": True,
    "files": [
        {"id": "1ABC", "name": "Doc.docx", "mimeType": "..."},
        # ...
    ],
    "has_more": True,
    "count": 10
}
```

---

## Agent API

### `EnhancedInventoryAgent`

Enhanced agent with inventory and Google Drive capabilities.

#### Constructor

```python
EnhancedInventoryAgent()
```

**Example:**
```python
from agents.enhanced_inventory_agent import EnhancedInventoryAgent

agent = EnhancedInventoryAgent()
```

#### Methods

##### `async run(input: str | list)`

Run the agent with a user query.

**Parameters:**
- `input` (str | list): User query or list of messages

**Returns:** `InventoryOutput | GDriveOutput`

**Example:**
```python
# Inventory query
result = await agent.run("Do we have laptops in stock?")
print(result)

# Google Drive query
result = await agent.run("Search for budget files")
print(result)
```

#### Available Tools

The agent has access to:

1. **`tool_check_inventory(product_name: str)`**
   - Checks product inventory
   - Returns: `InventoryOutput`

2. **`tool_gdrive_search(query: str)`**
   - Searches Google Drive files
   - Returns: `dict`

3. **`tool_gdrive_read(file_id: str)`**
   - Reads a file from Google Drive
   - Returns: `dict`

4. **`tool_gdrive_list()`**
   - Lists Google Drive files
   - Returns: `dict`

---

## Data Models

### `FileSearchResult`

```python
class FileSearchResult(BaseModel):
    files_found: int
    file_list: str
    query: str
```

**Example:**
```python
FileSearchResult(
    files_found=3,
    file_list="Report.docx\nBudget.xlsx\nSlides.pptx",
    query="quarterly"
)
```

### `FileContent`

```python
class FileContent(BaseModel):
    file_id: str
    mime_type: str
    content: str
    is_text: bool
```

**Example:**
```python
FileContent(
    file_id="1ABC123",
    mime_type="text/markdown",
    content="# Document Title\n\nContent...",
    is_text=True
)
```

### `FileListResult`

```python
class FileListResult(BaseModel):
    files: List[Dict[str, str]]
    has_more: bool
    next_cursor: Optional[str] = None
```

**Example:**
```python
FileListResult(
    files=[
        {"id": "1ABC", "name": "Doc.docx", "mimeType": "application/vnd..."},
        {"id": "2DEF", "name": "Sheet.xlsx", "mimeType": "application/vnd..."}
    ],
    has_more=True,
    next_cursor="token_123"
)
```

### `InventoryOutput`

```python
class InventoryOutput(BaseModel):
    product: str
    available: bool
    quantity: Optional[int] = None
```

**Example:**
```python
InventoryOutput(
    product="laptop",
    available=True,
    quantity=15
)
```

### `GDriveOutput`

```python
class GDriveOutput(BaseModel):
    operation: str
    success: bool
    data: Dict[str, Any]
```

**Example:**
```python
GDriveOutput(
    operation="search",
    success=True,
    data={"files_found": 3, "files": [...]}
)
```

---

## Error Handling

### Exception Types

#### `RuntimeError`

Raised when MCP server fails to start or communicate.

**Common Causes:**
- npx not found
- Credentials invalid
- Server process crashed

**Example:**
```python
try:
    async with get_gdrive_client() as client:
        results = await client.search_files("query")
except RuntimeError as e:
    print(f"MCP Error: {e}")
```

#### `FileNotFoundError`

Raised when Node.js/npx is not installed.

**Example:**
```python
try:
    client = GDriveMCPClient()
    await client.start()
except FileNotFoundError:
    print("Please install Node.js")
```

### Error Response Format

Tool functions return error information in the result dict:

```python
{
    "success": False,
    "error": "Error message",
    "file_id": "attempted_file_id"  # Context-specific
}
```

**Example:**
```python
result = await tool_read_gdrive_file("invalid_id")
if not result["success"]:
    print(f"Error: {result['error']}")
```

### Best Practices

#### 1. Always Use Context Manager

✅ **Good:**
```python
async with get_gdrive_client() as client:
    results = await client.search_files("query")
```

❌ **Bad:**
```python
client = GDriveMCPClient()
await client.start()
results = await client.search_files("query")
# Forgot to call client.stop()!
```

#### 2. Handle Errors Gracefully

✅ **Good:**
```python
try:
    result = await search_gdrive_files("query")
    if result.files_found > 0:
        print(result.file_list)
    else:
        print("No files found")
except Exception as e:
    print(f"Search failed: {e}")
```

#### 3. Validate File IDs

✅ **Good:**
```python
def is_valid_file_id(file_id: str) -> bool:
    return bool(file_id and len(file_id) > 0)

if is_valid_file_id(file_id):
    content = await read_gdrive_file(file_id)
```

#### 4. Use Type Hints

✅ **Good:**
```python
async def process_search_results(query: str) -> FileSearchResult:
    result = await search_gdrive_files(query)
    return result
```

#### 5. Handle Pagination

✅ **Good:**
```python
all_files = []
cursor = None

while True:
    result = await list_gdrive_files(cursor)
    all_files.extend(result.files)
    
    if not result.has_more:
        break
    cursor = result.next_cursor
```

---

## Complete Examples

### Example 1: Search and Read

```python
import asyncio
from tools.gdrive_tools import search_gdrive_files, read_gdrive_file

async def search_and_read_example():
    # Search for files
    search_result = await search_gdrive_files("quarterly report")
    
    print(f"Found {search_result.files_found} files")
    
    # Extract first file ID (you'd parse this from file_list in practice)
    file_id = "1ABC123XYZ"
    
    # Read the file
    content = await read_gdrive_file(file_id)
    
    if content.is_text:
        print(f"Content:\n{content.content}")
    else:
        print(f"Binary file: {content.mime_type}")

asyncio.run(search_and_read_example())
```

### Example 2: List All Files with Pagination

```python
import asyncio
from tools.gdrive_tools import list_gdrive_files

async def list_all_files():
    all_files = []
    cursor = None
    page = 1
    
    while True:
        print(f"Fetching page {page}...")
        result = await list_gdrive_files(cursor)
        
        all_files.extend(result.files)
        print(f"  Got {len(result.files)} files")
        
        if not result.has_more:
            break
        
        cursor = result.next_cursor
        page += 1
    
    print(f"\nTotal files: {len(all_files)}")
    for file in all_files:
        print(f"- {file['name']}")

asyncio.run(list_all_files())
```

### Example 3: Agent with Error Handling

```python
import asyncio
from agents.enhanced_inventory_agent import EnhancedInventoryAgent

async def agent_example():
    agent = EnhancedInventoryAgent()
    
    queries = [
        "Do we have laptops?",
        "Search Google Drive for reports",
        "List files from Google Drive"
    ]
    
    for query in queries:
        print(f"\nQuery: {query}")
        try:
            result = await agent.run(query)
            print(f"Result: {result}")
        except Exception as e:
            print(f"Error: {e}")

asyncio.run(agent_example())
```

### Example 4: Custom Tool Implementation

```python
from agents import function_tool
from tools.gdrive_tools import search_gdrive_files

@function_tool
async def custom_search_tool(category: str) -> dict:
    """
    Custom search tool that searches for specific categories.
    """
    query_map = {
        "reports": "quarterly OR annual report",
        "budgets": "budget OR financial plan",
        "presentations": "filetype:presentation"
    }
    
    query = query_map.get(category.lower(), category)
    result = await search_gdrive_files(query)
    
    return {
        "category": category,
        "files_found": result.files_found,
        "files": result.file_list
    }

# Use in agent
from agents.enhanced_inventory_agent import EnhancedInventoryAgent

agent = EnhancedInventoryAgent()
agent.tools.append(custom_search_tool)
```

---

## Environment Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `GDRIVE_CREDENTIALS_PATH` | Path to credentials file | `.gdrive-server-credentials.json` | Yes |
| `GDRIVE_OAUTH_PATH` | Path to OAuth keys file | `gcp-oauth.keys.json` | Yes (for auth) |
| `OPENAI_API_KEY` | OpenAI API key | None | Yes (for agent) |

**Example `.env` file:**
```bash
GDRIVE_CREDENTIALS_PATH=.gdrive-server-credentials.json
GDRIVE_OAUTH_PATH=gcp-oauth.keys.json
OPENAI_API_KEY=sk-...
```

---

## Rate Limits and Quotas

### Google Drive API

- **Queries per day**: 1,000,000,000
- **Queries per 100 seconds**: 12,000
- **Queries per 100 seconds per user**: 1,000

### Best Practices for Rate Limiting

1. **Cache results** when possible
2. **Batch operations** to reduce API calls
3. **Implement exponential backoff** for retries
4. **Monitor quota usage** in Google Cloud Console

---

## Troubleshooting API Issues

### Issue: "MCP Error: Connection refused"

**Solution:**
```python
# Check if credentials exist
import os
if not os.path.exists('.gdrive-server-credentials.json'):
    print("Run: python setup_gdrive.py")
```

### Issue: "Tool execution timeout"

**Solution:**
```python
# Increase timeout (if using asyncio)
import asyncio

result = await asyncio.wait_for(
    client.search_files("query"),
    timeout=30.0  # 30 seconds
)
```

### Issue: "Invalid file ID"

**Solution:**
```python
# Validate file ID format
import re

def validate_file_id(file_id: str) -> bool:
    # Google Drive file IDs are typically 25-50 characters
    return bool(re.match(r'^[a-zA-Z0-9_-]{25,50}$', file_id))
```

---

## Version Compatibility

| Component | Version | Notes |
|-----------|---------|-------|
| Python | 3.12+ | Required |
| Node.js | 18+ | For MCP server |
| openai-agents | 0.4.2+ | Agent SDK |
| mcp | 1.0.0+ | MCP SDK |
| @modelcontextprotocol/server-gdrive | Latest | NPM package |

---

For more information, see:
- [README.md](README.md) - Full documentation
- [QUICKSTART.md](QUICKSTART.md) - Quick setup guide
- [ARCHITECTURE.md](ARCHITECTURE.md) - System architecture
- [INTEGRATION_SUMMARY.md](INTEGRATION_SUMMARY.md) - Implementation details
