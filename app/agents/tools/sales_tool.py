"""Sales-related tool functions moved out of the agent file.

These are decorated with the SDK's @function_tool so the agent runtime
can call them as tools. Keep this module simple and focused on product
lookups (uses the MCP server PRODUCTS_DB).
"""
from agents import function_tool
from typing import List
from app.mcp_server.server import PRODUCTS_DB


@function_tool
def lookup_product(query: str) -> str:
    """Look up product information by product type or name using PRODUCTS_DB."""
    query_lower = query.lower()
    if query_lower in PRODUCTS_DB:
        product = PRODUCTS_DB[query_lower]
        return f"{product['name']}: ${product['price']} – {product['description']}"
    return f"No match for '{query}' – describe what you need!"


@function_tool
def list_all_products() -> str:
    """Return a short bulleted list of all products."""
    products_list: List[str] = []
    for key, product in PRODUCTS_DB.items():
        products_list.append(f"• {product['name']} (${product['price']}): {product['description']}")
    return "Available Products:\n" + "\n".join(products_list)


@function_tool
def get_product_by_price_range(min_price: int, max_price: int) -> str:
    """Find products within a specific price range."""
    matching_products: List[str] = []
    for key, product in PRODUCTS_DB.items():
        try:
            price = float(product.get("price", 0))
        except Exception:
            continue
        if min_price <= price <= max_price:
            matching_products.append(f"• {product['name']} (${product['price']}): {product['description']}")
    if matching_products:
        return f"Products between ${min_price}-${max_price}:\n" + "\n".join(matching_products)
    return f"No products found between ${min_price}-${max_price}"


@function_tool
def get_product_by_category(category: str) -> str:
    """Find products by category."""
    category_lower = category.lower()
    matching_products: List[str] = []
    for key, product in PRODUCTS_DB.items():
        if product.get('category') == category_lower:
            matching_products.append(f"• {product['name']} (${product['price']}): {product['description']}")
    if matching_products:
        return f"{category.title()} Products:\n" + "\n".join(matching_products)
    return f"No products found in category '{category}'"
