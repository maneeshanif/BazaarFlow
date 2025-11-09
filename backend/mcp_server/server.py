"""
BazaarFlow MCP Server
Provides product lookup and sales tools for the sales agent
"""

from fastmcp import FastMCP
import logging
# Configure basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Initialize the MCP server
mcp = FastMCP(name="BazaarFlow Sales Tools", stateless_http=True,
    json_response=True, # Generally easier for HTTP clients if they don't need full SSE parsing
    )

# Product database
PRODUCTS_DB = {
    "phone": {
        "name": "iPhone 15",
        "price": 999,
        "description": "AI camera, battery life for busy reps.",
        "category": "mobile"
    },
    "laptop": {
        "name": "MacBook Pro",
        "price": 1999,
        "description": "M3 chip, perfect for on-the-go sales.",
        "category": "computer"
    },
    "tablet": {
        "name": "iPad Pro",
        "price": 799,
        "description": "Portable powerhouse for presentations.",
        "category": "mobile"
    },
    "watch": {
        "name": "Apple Watch Ultra",
        "price": 799,
        "description": "Stay connected during client meetings.",
        "category": "wearable"
    }
}


@mcp.tool()
def lookup_product(query: str) -> str:
    """
    Look up product information by product type or name.
    
    Args:
        query: The product type to search for (e.g., 'phone', 'laptop', 'tablet', 'watch')
    
    Returns:
        Product details including name, price, and description
    """
    query_lower = query.lower()
    
    if query_lower in PRODUCTS_DB:
        product = PRODUCTS_DB[query_lower]
        return f"{product['name']}: ${product['price']} – {product['description']}"
    
    return f"No match for '{query}' – describe what you need!"


@mcp.tool()
def list_all_products() -> str:
    """
    List all available products in the catalog.
    
    Returns:
        A formatted list of all products with their prices and descriptions
    """
    products_list = []
    for key, product in PRODUCTS_DB.items():
        products_list.append(
            f"• {product['name']} (${product['price']}): {product['description']}"
        )
    
    return "Available Products:\n" + "\n".join(products_list)


@mcp.tool()
def get_product_by_price_range(min_price: int, max_price: int) -> str:
    """
    Find products within a specific price range.
    
    Args:
        min_price: Minimum price in dollars
        max_price: Maximum price in dollars
    
    Returns:
        List of products within the specified price range
    """
    matching_products = []
    
    for key, product in PRODUCTS_DB.items():
        if min_price <= product['price'] <= max_price:
            matching_products.append(
                f"• {product['name']} (${product['price']}): {product['description']}"
            )
    
    if matching_products:
        return f"Products between ${min_price}-${max_price}:\n" + "\n".join(matching_products)
    
    return f"No products found between ${min_price}-${max_price}"


@mcp.tool()
def get_product_by_category(category: str) -> str:
    """
    Find products by category.
    
    Args:
        category: Product category ('mobile', 'computer', 'wearable')
    
    Returns:
        List of products in the specified category
    """
    category_lower = category.lower()
    matching_products = []
    
    for key, product in PRODUCTS_DB.items():
        if product['category'] == category_lower:
            matching_products.append(
                f"• {product['name']} (${product['price']}): {product['description']}"
            )
    
    if matching_products:
        return f"{category.title()} Products:\n" + "\n".join(matching_products)
    
    return f"No products found in category '{category}'"


if __name__ == "__main__":
    port = 8001
    streamable_http_app = mcp_app.streamable_http_app()
    logger.info(f"Starting {streamable_http_app}")
    import uvicorn
    # uvicorn.run(streamable_http_app, host="0.0.0.0", port=port)
    # start with hot reload
    uvicorn.run("mood_server:mcp_app.streamable_http_app", host="0.0.0.0", port=port, reload=True)