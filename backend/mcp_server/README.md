# BazaarFlow MCP Server

This is the Model Context Protocol (MCP) server for BazaarFlow Sales Tools, built with FastMCP.

## Overview

The MCP server provides product lookup and sales tools that can be used by the sales agent to provide accurate product information to customers.

## Features

The server exposes the following tools:

### 1. `lookup_product(query: str)`
Look up a specific product by type or name.

**Parameters:**
- `query`: Product type to search for (e.g., 'phone', 'laptop', 'tablet', 'watch')

**Returns:** Product details including name, price, and description

**Example:**
```python
lookup_product("phone")
# Returns: "iPhone 15: $999 – AI camera, battery life for busy reps."
```

### 2. `list_all_products()`
List all available products in the catalog.

**Returns:** A formatted list of all products with prices and descriptions

**Example:**
```python
list_all_products()
# Returns all products in catalog
```

### 3. `get_product_by_price_range(min_price: int, max_price: int)`
Find products within a specific price range.

**Parameters:**
- `min_price`: Minimum price in dollars
- `max_price`: Maximum price in dollars

**Returns:** List of products within the specified price range

**Example:**
```python
get_product_by_price_range(500, 1000)
# Returns products between $500-$1000
```

### 4. `get_product_by_category(category: str)`
Find products by category.

**Parameters:**
- `category`: Product category ('mobile', 'computer', 'wearable')

**Returns:** List of products in the specified category

**Example:**
```python
get_product_by_category("mobile")
# Returns all mobile products
```

## Product Database

The server maintains a product database with the following items:

- **iPhone 15** - $999 (Mobile)
- **MacBook Pro** - $1999 (Computer)
- **iPad Pro** - $799 (Mobile)
- **Apple Watch Ultra** - $799 (Wearable)

## Running the MCP Server

### Standalone Mode
To run the MCP server standalone:

```bash
cd backend/mcp_server
python server.py
```

### Integration with Sales Agent

The sales agent in `backend/my_agents/sales_agent.py` is already configured to use this MCP server. The agent imports the tools and product database directly.

## Agent MCP Properties

The sales agent has been configured with the following MCP-related properties:

```python
sales_agent = Agent(
    # ... other config ...
    tools=[lookup_product, list_all_products, get_product_by_price_range, get_product_by_category],
    mcp_server_enabled=True,
    mcp_server_path="/path/to/backend/mcp_server",
    mcp_server_name="BazaarFlow Sales Tools"
)
```

## Architecture

```
backend/
├── mcp_server/
│   ├── __init__.py          # Package initialization
│   ├── server.py            # Main MCP server with tools
│   └── README.md            # This file
└── my_agents/
    └── sales_agent.py       # Sales agent with MCP integration
```

## Dependencies

- **fastmcp**: Framework for building MCP servers
- **openai-agents**: Agent framework with tool support

## Adding New Products

To add new products to the database, edit the `PRODUCTS_DB` dictionary in `server.py`:

```python
PRODUCTS_DB = {
    "new_product": {
        "name": "Product Name",
        "price": 999,
        "description": "Product description",
        "category": "category_name"
    }
}
```

## Adding New Tools

To add new tools to the MCP server:

1. Define the tool function with the `@mcp.tool()` decorator in `server.py`
2. Add the tool to the agent's tools list in `sales_agent.py`
3. Update the agent's instructions to include usage of the new tool

Example:
```python
@mcp.tool()
def new_tool(param: str) -> str:
    """Tool description"""
    # Implementation
    return result
```

## Testing

To test the MCP server tools, you can import them in a Python script:

```python
from mcp_server.server import lookup_product, list_all_products

# Test lookup
result = lookup_product("phone")
print(result)

# Test list all
all_products = list_all_products()
print(all_products)
```

## Troubleshooting

### Import Errors
If you encounter import errors, ensure that:
1. fastmcp is installed: `uv add fastmcp`
2. The backend directory is in your Python path
3. All `__init__.py` files are present

### MCP Server Not Found
If the agent can't find the MCP server:
1. Check that `mcp_server_path` in the agent config is correct
2. Verify that `server.py` exists in the mcp_server directory
3. Ensure PRODUCTS_DB is properly imported

## License

Part of the BazaarFlow project.
