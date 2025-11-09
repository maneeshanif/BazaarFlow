# Quick Start Guide - Google Drive MCP Integration

This guide will help you get up and running with the Google Drive MCP integration in under 10 minutes.

## Prerequisites Checklist

Before you begin, ensure you have:

- [ ] **Node.js** (v18+) installed - [Download here](https://nodejs.org/)
- [ ] **Python 3.12+** installed
- [ ] **Google Cloud Account** - [Sign up here](https://cloud.google.com/)
- [ ] **Google Drive** with some files in it

## Step-by-Step Setup

### Step 1: Set up Google Cloud Project (5 minutes)

1. **Create Project**
   - Go to: https://console.cloud.google.com/projectcreate
   - Project name: `inventory-mcp-server`
   - Click "Create"

2. **Enable Google Drive API**
   - Go to: https://console.cloud.google.com/workspace-api/products
   - Click "Enable APIs and Services"
   - Search for "Google Drive API"
   - Click "Enable"

3. **Configure OAuth Consent Screen**
   - Go to: https://console.cloud.google.com/apis/credentials/consent
   - Choose "Internal" (or "External" if not in an organization)
   - Fill in:
     - App name: `Inventory MCP Server`
     - User support email: Your email
     - Developer contact: Your email
   - Click "Save and Continue"

4. **Add OAuth Scope**
   - On the "Scopes" page, click "Add or Remove Scopes"
   - Filter for: `drive.readonly`
   - Check the box for: `https://www.googleapis.com/auth/drive.readonly`
   - Click "Update" → "Save and Continue"

5. **Create OAuth Client ID**
   - Go to: https://console.cloud.google.com/apis/credentials/oauthclient
   - Application type: "Desktop App"
   - Name: `Inventory MCP Desktop Client`
   - Click "Create"
   - Click "Download JSON"
   - Save and rename the file to: `gcp-oauth.keys.json`
   - Move it to your project root directory

### Step 2: Install Dependencies (1 minute)

```bash
# Install Python dependencies
pip install -e .

# Verify Node.js is installed
node --version
# Should show v18.0.0 or higher
```

### Step 3: Authenticate with Google Drive (2 minutes)

```bash
# Run the setup script
python setup_gdrive.py
```

This will:
1. Check your Node.js installation
2. Verify your OAuth keys
3. Open a browser for authentication
4. Save credentials to `.gdrive-server-credentials.json`

**Follow the browser prompts:**
1. Select your Google account
2. Click "Continue" to grant permissions
3. You may see a warning if the app is not verified - click "Advanced" → "Go to [App Name] (unsafe)"
4. Click "Allow" to grant Drive read access

### Step 4: Verify Setup (1 minute)

```bash
# Run the test script
python test_gdrive.py
```

You should see:
- ✓ Connection Test: PASSED
- ✓ Tool Function Test: PASSED

### Step 5: Try It Out! (1 minute)

```bash
# Run the example
python example_usage.py
```

Or use it programmatically:

```python
import asyncio
from agents.enhanced_inventory_agent import EnhancedInventoryAgent

async def demo():
    agent = EnhancedInventoryAgent()
    
    # Search for files
    result = await agent.run("Find files about reports")
    print(result)
    
    # List files
    result = await agent.run("List all files")
    print(result)

asyncio.run(demo())
```

## Common Issues & Solutions

### Issue: "npx not found"
**Solution:** Install Node.js from https://nodejs.org/

### Issue: "OAuth error"
**Solution:** 
1. Make sure `gcp-oauth.keys.json` is in the project root
2. Verify you added the correct OAuth scope: `drive.readonly`
3. Try re-authenticating: `python setup_gdrive.py`

### Issue: "Credentials not found"
**Solution:** Run authentication first: `python setup_gdrive.py`

### Issue: "Access denied"
**Solution:** 
1. Check OAuth consent screen is configured
2. Make sure you're using the correct Google account
3. Verify the app has the Drive read scope

### Issue: Import errors
**Solution:** Install dependencies: `pip install -e .`

## What's Next?

Now that you're set up, you can:

1. **Customize the Agent**
   - Edit `agents/enhanced_inventory_agent.py`
   - Add more tools or modify existing ones

2. **Add More Google Drive Features**
   - Edit `tools/gdrive_tools.py`
   - Implement file creation, updates, etc.

3. **Integrate with Your App**
   - Import the agent into your application
   - Use it in your API endpoints

4. **Explore More MCP Servers**
   - Check out: https://github.com/modelcontextprotocol/servers
   - Add Slack, GitHub, or other integrations

## Security Reminders

⚠️ **Never commit these files:**
- `gcp-oauth.keys.json` - OAuth client secrets
- `.gdrive-server-credentials.json` - Your access tokens
- `.env` - API keys and configuration

They're already in `.gitignore`, but double-check before committing!

## Getting Help

If you're stuck:

1. Check the main README.md for detailed documentation
2. Review the Troubleshooting section
3. Check the Google Drive MCP server docs: https://github.com/modelcontextprotocol/servers-archived/tree/main/src/gdrive
4. Open an issue on the project repository

## Useful Commands

```bash
# Run setup/authentication
python setup_gdrive.py

# Test the integration
python test_gdrive.py

# Run the example
python example_usage.py

# Install/update dependencies
pip install -e .

# Check Node.js version
node --version

# Test MCP server manually
npx -y @modelcontextprotocol/server-gdrive
```

---

**Congratulations!** 🎉 You're now ready to use Google Drive with your AI agent!
