# Google Drive MCP Integration Architecture

## System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                           User Application                          │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐  │
│  │         Enhanced Inventory Agent                             │  │
│  │  (agents/enhanced_inventory_agent.py)                        │  │
│  │                                                               │  │
│  │  Instructions: Handle inventory + Google Drive queries       │  │
│  │  Model: OpenAI GPT-4 (or compatible)                        │  │
│  │  Guardrails: Input + Output validation                      │  │
│  └──────────────────┬──────────────────────────────────────────┘  │
│                     │                                              │
│                     │ Function Calling                             │
│                     ▼                                              │
│  ┌─────────────────────────────────────────────────────────────┐  │
│  │                    Function Tools (4)                        │  │
│  │                                                               │  │
│  │  ┌─────────────────┐    ┌──────────────────────────────┐   │  │
│  │  │ Inventory Tool  │    │  Google Drive Tools (3)      │   │  │
│  │  │                 │    │                              │   │  │
│  │  │ - check         │    │ - search_files               │   │  │
│  │  │   inventory     │    │ - read_file                  │   │  │
│  │  │                 │    │ - list_files                 │   │  │
│  │  └────────┬────────┘    └──────────┬───────────────────┘   │  │
│  └───────────┼──────────────────────────┼───────────────────────┘  │
│              │                          │                          │
└──────────────┼──────────────────────────┼──────────────────────────┘
               │                          │
               │                          │
               ▼                          ▼
     ┌─────────────────┐      ┌──────────────────────┐
     │  Inventory Tool │      │ Google Drive Tools   │
     │  (Local)        │      │ (tools/gdrive_*.py)  │
     │                 │      │                      │
     │ - Reads from    │      │ - search_gdrive_*()  │
     │   JSON file     │      │ - read_gdrive_*()    │
     │                 │      │ - list_gdrive_*()    │
     └─────────────────┘      └──────────┬───────────┘
                                         │
                                         │ Async calls
                                         ▼
                              ┌──────────────────────┐
                              │  GDrive MCP Client   │
                              │  (Python)            │
                              │                      │
                              │ - Manages stdio      │
                              │ - JSON-RPC protocol  │
                              │ - Connection pool    │
                              └──────────┬───────────┘
                                         │
                                         │ stdio (stdin/stdout)
                                         ▼
                              ┌──────────────────────┐
                              │  NPX Process         │
                              │                      │
                              │ npx -y @model...     │
                              │   server-gdrive      │
                              └──────────┬───────────┘
                                         │
                                         │ Spawns
                                         ▼
                              ┌──────────────────────┐
                              │ Google Drive MCP     │
                              │ Server (Node.js)     │
                              │                      │
                              │ - Resources API      │
                              │ - Tools API          │
                              │ - File conversion    │
                              └──────────┬───────────┘
                                         │
                                         │ OAuth 2.0 + HTTPS
                                         ▼
                              ┌──────────────────────┐
                              │  Google Drive API    │
                              │                      │
                              │ - File listing       │
                              │ - File reading       │
                              │ - Search             │
                              └──────────────────────┘
```

## Data Flow Examples

### Example 1: Inventory Query

```
User: "Do we have laptops in stock?"
  │
  ├─> Agent analyzes query
  │
  ├─> Selects: tool_check_inventory("laptop")
  │
  ├─> Reads: data/mock_inventory.json
  │
  ├─> Returns: InventoryOutput(product="laptop", available=True, quantity=15)
  │
  └─> Agent responds: "Yes, we have 15 laptops in stock."
```

### Example 2: Google Drive Search

```
User: "Find files about quarterly reports"
  │
  ├─> Agent analyzes query
  │
  ├─> Selects: tool_gdrive_search("quarterly reports")
  │
  ├─> Calls: search_gdrive_files("quarterly reports")
  │
  ├─> Client initializes: GDriveMCPClient()
  │
  ├─> Spawns: npx @modelcontextprotocol/server-gdrive
  │
  ├─> Sends JSON-RPC: {"method": "tools/call", "params": {"name": "search", ...}}
  │
  ├─> MCP Server queries Google Drive API
  │
  ├─> Returns: {"content": [{"text": "Found 3 files:\nQ1 Report.docx\n..."}]}
  │
  ├─> Parses result into FileSearchResult
  │
  └─> Agent responds: "I found 3 files: Q1 Report.docx, Q2 Report.pdf, ..."
```

### Example 3: Read File

```
User: "Read file ID 1ABC123XYZ"
  │
  ├─> Agent analyzes query
  │
  ├─> Selects: tool_gdrive_read("1ABC123XYZ")
  │
  ├─> Calls: read_gdrive_file("1ABC123XYZ")
  │
  ├─> Client sends: {"method": "resources/read", "params": {"uri": "gdrive:///1ABC123XYZ"}}
  │
  ├─> MCP Server:
  │   ├─> Gets file metadata
  │   ├─> Checks MIME type
  │   └─> Exports if Google Workspace file (Docs → Markdown)
  │
  ├─> Returns: {"contents": [{"text": "# Document Content\n...", "mimeType": "text/markdown"}]}
  │
  ├─> Parses into FileContent
  │
  └─> Agent responds: "Here's the content: # Document Content\n..."
```

## Communication Protocol

### JSON-RPC Messages

#### Request Format
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "search",
    "arguments": {
      "query": "budget"
    }
  }
}
```

#### Response Format
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "content": [
      {
        "type": "text",
        "text": "Found 2 files:\nBudget 2024.xlsx (application/vnd...)\n..."
      }
    ],
    "isError": false
  }
}
```

#### Error Format
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "error": {
    "code": -32000,
    "message": "File not found",
    "data": {
      "fileId": "invalid_id"
    }
  }
}
```

## File Conversion Matrix

| Google Workspace Type | Export Format | MIME Type |
|----------------------|---------------|-----------|
| Google Docs | Markdown | text/markdown |
| Google Sheets | CSV | text/csv |
| Google Slides | Plain Text | text/plain |
| Google Drawings | PNG | image/png |
| PDF | Binary | application/pdf |
| Text files | Text | text/plain |
| Images | Binary | image/* |

## Component Responsibilities

### Python Layer (Application)

```
┌─────────────────────────────────────────────┐
│ Enhanced Inventory Agent                    │
│ ─────────────────────────────────────────── │
│ • Orchestrates tool selection               │
│ • Interprets user queries                   │
│ • Applies guardrails                        │
│ • Formats responses                         │
└─────────────────────────────────────────────┘

┌─────────────────────────────────────────────┐
│ Google Drive Tools                          │
│ ─────────────────────────────────────────── │
│ • High-level abstractions                   │
│ • Pydantic models                           │
│ • Error handling                            │
│ • Result parsing                            │
└─────────────────────────────────────────────┘

┌─────────────────────────────────────────────┐
│ GDrive MCP Client                           │
│ ─────────────────────────────────────────── │
│ • Process management                        │
│ • stdio communication                       │
│ • JSON-RPC implementation                   │
│ • Connection lifecycle                      │
└─────────────────────────────────────────────┘
```

### Node.js Layer (MCP Server)

```
┌─────────────────────────────────────────────┐
│ Google Drive MCP Server                     │
│ ─────────────────────────────────────────── │
│ • OAuth credential management               │
│ • Google Drive API client                   │
│ • File type detection                       │
│ • Export/conversion logic                   │
│ • Resource & tool endpoints                 │
└─────────────────────────────────────────────┘
```

## Security Layers

```
┌─────────────────────────────────────────────┐
│ Application Layer                           │
│ ─────────────────────────────────────────── │
│ • Input guardrails                          │
│ • Output validation                         │
│ • Query sanitization                        │
└─────────────────────────────────────────────┘
                    ▼
┌─────────────────────────────────────────────┐
│ Transport Layer                             │
│ ─────────────────────────────────────────── │
│ • stdio isolation                           │
│ • Process boundaries                        │
│ • JSON-RPC protocol                         │
└─────────────────────────────────────────────┘
                    ▼
┌─────────────────────────────────────────────┐
│ Authentication Layer                        │
│ ─────────────────────────────────────────── │
│ • OAuth 2.0                                 │
│ • Token refresh                             │
│ • Read-only scope                           │
└─────────────────────────────────────────────┘
                    ▼
┌─────────────────────────────────────────────┐
│ API Layer                                   │
│ ─────────────────────────────────────────── │
│ • HTTPS encryption                          │
│ • Google API security                       │
│ • Rate limiting                             │
└─────────────────────────────────────────────┘
```

## Error Handling Flow

```
┌─────────────────────┐
│   User Query        │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐     Error?
│  Input Guardrails   ├─────────► Validation Error Response
└──────────┬──────────┘              ▲
           │                         │
           ▼                         │
┌─────────────────────┐     Error?  │
│  Tool Selection     ├─────────────┤
└──────────┬──────────┘              │
           │                         │
           ▼                         │
┌─────────────────────┐     Error?  │
│  Tool Execution     ├─────────────┤
│  (with try/catch)   │              │
└──────────┬──────────┘              │
           │                         │
           ▼                         │
┌─────────────────────┐     Error?  │
│  MCP Communication  ├─────────────┤
└──────────┬──────────┘              │
           │                         │
           ▼                         │
┌─────────────────────┐     Error?  │
│  Result Parsing     ├─────────────┤
└──────────┬──────────┘              │
           │                         │
           ▼                         │
┌─────────────────────┐     Error?  │
│  Output Guardrails  ├─────────────┘
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│   User Response     │
└─────────────────────┘
```

## Scalability Considerations

### Horizontal Scaling
```
┌──────────┐  ┌──────────┐  ┌──────────┐
│ Agent 1  │  │ Agent 2  │  │ Agent N  │
└────┬─────┘  └────┬─────┘  └────┬─────┘
     │             │              │
     └─────────────┼──────────────┘
                   │
                   ▼
         ┌──────────────────┐
         │  MCP Client Pool  │
         │  (Connection)     │
         │  Management)      │
         └─────────┬─────────┘
                   │
                   ▼
         ┌──────────────────┐
         │  Google Drive    │
         │  API             │
         └──────────────────┘
```

### Performance Optimization
```
┌─────────────────────────────────────┐
│ Cache Layer (Optional)              │
│ ───────────────────────────────────│
│ • Search results (TTL: 5 min)       │
│ • File metadata (TTL: 10 min)       │
│ • File content (TTL: 1 hour)        │
└─────────────────────────────────────┘
                 ▼
┌─────────────────────────────────────┐
│ Connection Pool                     │
│ ───────────────────────────────────│
│ • Reuse MCP connections             │
│ • Max 10 concurrent connections     │
│ • Idle timeout: 5 minutes           │
└─────────────────────────────────────┘
```

## Monitoring Points

```
┌─────────────────────────────────────┐
│ Metrics to Track                    │
│ ───────────────────────────────────│
│ • Agent query latency               │
│ • MCP connection time               │
│ • Google Drive API response time    │
│ • Error rates by type               │
│ • Tool usage frequency              │
│ • Token refresh success rate        │
└─────────────────────────────────────┘
```

---

This architecture provides:
- ✅ Clean separation of concerns
- ✅ Scalable design
- ✅ Robust error handling
- ✅ Security at multiple layers
- ✅ Easy to extend and maintain
