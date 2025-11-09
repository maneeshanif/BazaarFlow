# Inventory MCP Server with Google Drive Integration

An intelligent inventory management system integrated with Google Drive using the Model Context Protocol (MCP). This agent can check product inventory and access Google Drive files for document management.

## Features

- ✅ **Inventory Management**: Check product availability and quantities
- 🗂️ **Google Drive Integration**: Search, read, and list files from Google Drive
- 🤖 **AI-Powered Agent**: Uses OpenAI Agents SDK with function calling
- 🔒 **Guardrails**: Input and output validation for safe operations
- 🔌 **MCP Protocol**: Leverages Model Context Protocol for Google Drive access

## Prerequisites

Before setting up this project, ensure you have:

1. **Node.js and npm** (v18 or higher) - Required for the Google Drive MCP server
2. **Python 3.12+** - For the agent application
3. **Google Cloud Account** - For Google Drive API access
4. **OpenAI API Key** - For the AI agent (if using OpenAI models)

## Google Drive MCP Server Setup

Follow these steps to set up Google Drive API access:

### 1. Create Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/projectcreate)
2. Create a new project (e.g., "inventory-mcp-server")
3. Note your project ID

### 2. Enable Google Drive API

1. Visit [Google Workspace API Products](https://console.cloud.google.com/workspace-api/products)
2. Enable the **Google Drive API** for your project

### 3. Configure OAuth Consent Screen

1. Go to [OAuth Consent Screen](https://console.cloud.google.com/apis/credentials/consent)
2. Choose "Internal" (for testing within your organization) or "External"
3. Fill in the required information:
   - App name: "Inventory MCP Server"
   - User support email: Your email
   - Developer contact: Your email
4. Click "Save and Continue"

### 4. Add OAuth Scopes

1. On the "Scopes" page, click "Add or Remove Scopes"
2. Add the following scope:
   ```
   https://www.googleapis.com/auth/drive.readonly
   ```
3. Click "Update" and then "Save and Continue"

### 5. Create OAuth Client ID

1. Go to [Create OAuth Client ID](https://console.cloud.google.com/apis/credentials/oauthclient)
2. Select "Desktop App" as the application type
3. Name it "Inventory MCP Desktop Client"
4. Click "Create"
5. Download the JSON file
6. Rename it to `gcp-oauth.keys.json`
7. Place it in the root of this project

### 6. Authenticate the Google Drive MCP Server

You need to authenticate once to generate credentials:

```bash
# Option 1: Using npx (recommended)
npx -y @modelcontextprotocol/server-gdrive

# The server will provide a URL - open it in your browser
# Complete the OAuth flow
# Credentials will be saved to .gdrive-server-credentials.json
```

If you encounter issues, you can set the paths explicitly:

```bash
# Set environment variables
export GDRIVE_OAUTH_PATH=./gcp-oauth.keys.json
export GDRIVE_CREDENTIALS_PATH=./.gdrive-server-credentials.json

# Run authentication
npx -y @modelcontextprotocol/server-gdrive
```

After successful authentication, you should have a `.gdrive-server-credentials.json` file in your project root.

## Project Setup

### 1. Clone and Install Dependencies

```bash
# Install Python dependencies
pip install -e .

# Or using uv (recommended)
uv pip install -e .
```

### 2. Configure Environment Variables

Copy the example environment file and configure it:

```bash
cp .env.example .env
```

Edit `.env` with your values:

```bash
# Google Drive credentials (generated after OAuth)
GDRIVE_CREDENTIALS_PATH=.gdrive-server-credentials.json

# Google OAuth keys (downloaded from Google Cloud Console)
GDRIVE_OAUTH_PATH=gcp-oauth.keys.json

# OpenAI API key (if using OpenAI models)
OPENAI_API_KEY=your_openai_api_key_here
```

### 3. Verify Setup

Test that the Google Drive MCP server is working:

```bash
# This should start the server and connect successfully
npx -y @modelcontextprotocol/server-gdrive
```

## Usage

### Running the Agent

```python
from agents.enhanced_inventory_agent import EnhancedInventoryAgent

# Create agent instance
agent = EnhancedInventoryAgent()

# Check inventory
result = await agent.run("Do we have any laptops in stock?")
print(result)

# Search Google Drive
result = await agent.run("Find files related to quarterly reports")
print(result)

# Read a Google Drive file
result = await agent.run("Read the file with ID 1ABC...XYZ")
print(result)

# List files
result = await agent.run("List all available files in Google Drive")
print(result)
```

### Available Tools

The agent has access to the following tools:

#### 1. **Inventory Tools**
- `tool_check_inventory(product_name: str)` - Check product availability and quantity

#### 2. **Google Drive Tools**
- `tool_gdrive_search(query: str)` - Search for files in Google Drive
- `tool_gdrive_read(file_id: str)` - Read content from a specific file
- `tool_gdrive_list()` - List available files from Google Drive

### Example Queries

```python
# Inventory queries
"Is the iPhone 14 in stock?"
"How many MacBook Pros do we have?"
"Check availability of wireless mouse"

# Google Drive queries
"Search for budget spreadsheets"
"Find files about Q4 performance"
"List all files in Google Drive"
"Read the content of file 1A2B3C4D5E6F"
```

## Project Structure

```
inventory-mcp-server/
├── agents/
│   ├── inventory_agent.py           # Original inventory agent
│   └── enhanced_inventory_agent.py  # Enhanced agent with Google Drive
├── tools/
│   ├── inventory_tool.py            # Local inventory checking
│   ├── mcp_client.py                # Generic MCP client
│   ├── gdrive_mcp_client.py         # Google Drive MCP client wrapper
│   └── gdrive_tools.py              # Google Drive tool functions
├── guardrails/
│   ├── input_guardrail.py           # Input validation
│   └── output_guardrail.py          # Output validation
├── data/
│   └── mock_inventory.json          # Mock inventory data
├── gcp-oauth.keys.json              # Google OAuth keys (do not commit!)
├── .gdrive-server-credentials.json  # Generated credentials (do not commit!)
├── .env                             # Environment variables (do not commit!)
├── .env.example                     # Example environment file
├── pyproject.toml                   # Python dependencies
└── README.md                        # This file
```

## Google Drive MCP Server Components

### Tools
- **search**: Search for files in Google Drive by query string

### Resources
The MCP server provides access to Google Drive files:
- **Files** (`gdrive:///<file_id>`)
  - Supports all file types
  - Google Workspace files are automatically exported:
    - Docs → Markdown
    - Sheets → CSV
    - Presentations → Plain text
    - Drawings → PNG
  - Other files in native format

## Troubleshooting

### Common Issues

#### 1. "npx not found"
**Solution**: Install Node.js from [nodejs.org](https://nodejs.org/)

#### 2. "Credentials not found"
**Solution**: Run the authentication flow first:
```bash
npx -y @modelcontextprotocol/server-gdrive
```

#### 3. "OAuth error" or "Access denied"
**Solution**: 
- Verify you added the correct OAuth scope: `https://www.googleapis.com/auth/drive.readonly`
- Check that your `gcp-oauth.keys.json` file is in the project root
- Ensure OAuth consent screen is properly configured

#### 4. "MCP server not responding"
**Solution**:
- Ensure Node.js is installed and in your PATH
- Check that the credentials file path in `.env` is correct
- Try running the MCP server manually to see error messages

#### 5. Import errors
**Solution**: Install dependencies:
```bash
pip install -e .
# or
uv pip install -e .
```

## Security Notes

⚠️ **Important**: Never commit sensitive files to version control:
- `gcp-oauth.keys.json` - Contains your OAuth client secrets
- `.gdrive-server-credentials.json` - Contains your access/refresh tokens
- `.env` - Contains API keys and configuration

Add these to your `.gitignore`:
```gitignore
gcp-oauth.keys.json
.gdrive-server-credentials.json
.env
*.pyc
__pycache__/
```

## Development

### Adding More Google Drive Capabilities

To extend functionality, modify `tools/gdrive_tools.py`:

```python
async def tool_create_file(name: str, content: str) -> dict:
    """Example: Create a new file in Google Drive"""
    async with get_gdrive_client() as client:
        # Implement file creation logic
        pass
```

### Testing

```bash
# Test inventory tools
python -m pytest tests/test_inventory.py

# Test Google Drive integration
python -m pytest tests/test_gdrive.py
```

## References

- [Model Context Protocol Documentation](https://modelcontextprotocol.io/)
- [Google Drive MCP Server Docs](https://github.com/modelcontextprotocol/servers-archived/tree/main/src/gdrive)
- [Google Drive API Documentation](https://developers.google.com/drive/api)
- [OpenAI Agents SDK](https://github.com/openai/openai-python)

## License

MIT License - See LICENSE file for details

## Support

For issues or questions:
1. Check the Troubleshooting section above
2. Review the Google Drive MCP server documentation
3. Open an issue on the project repository

---

**Note**: This implementation uses the archived Google Drive MCP server. For the latest maintained version, check the [official MCP servers repository](https://github.com/modelcontextprotocol/servers).
