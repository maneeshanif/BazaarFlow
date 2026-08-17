"""Tool functions powering the inventory agent."""
from typing import Any

from agents import function_tool

from app.services.inventory_service import inventory_analytics_service


def _format_stock_bucket(detail: dict[str, dict[str, Any]]) -> str:
    parts: list[str] = []
    mapping = {
        "in_stock": "✅ In stock",
        "low_stock": "⚠️ Low stock",
        "out_of_stock": "❌ Out of stock",
    }
    for key, label in mapping.items():
        bucket = detail.get(key, {"count": 0, "total_units": 0, "items": []})
        header = f"{label}: {bucket['count']} items · {bucket['total_units']} units"
        items: list[dict[str, Any]] = list(bucket.get("items", []))
        if items:
            item_lines = "\n".join(
                f"   • {item['name']} ({item['stock']} in stock, {item['incoming']} incoming)"
                for item in items
            )
            parts.append(f"{header}\n{item_lines}")
        else:
            parts.append(f"{header}\n   • None 🎉")
    return "\n".join(parts)


@function_tool
def inventory_stock_overview() -> str:
    """Summarise overall stock health (in stock, low stock, out of stock)."""
    detail = inventory_analytics_service.get_stock_health_detail()
    return "📦 Inventory Overview\n" + _format_stock_bucket(detail)


@function_tool
def inventory_restock_alerts(limit: int = 3) -> str:
    """List SKUs that require restocking soon."""
    queue = inventory_analytics_service.get_restock_queue(limit=limit)
    if not queue:
        return "🎉 All items are comfortably above their reorder points."

    lines: list[str] = []
    for item in queue:
        lines.append(
            f"• {item['name']}: {item['stock']} units in stock, incoming {item['incoming']}"
        )
    return "⚠️ Restock Queue\n" + "\n".join(lines)


@function_tool
def inventory_category_summary(category: str) -> str:
    """Show stock and items for a specific category (e.g., mobile)."""
    items = inventory_analytics_service.get_items_by_category(category)
    if not items:
        return f"No items found for category '{category}'."

    total_units = sum(int(item.get("stock", 0)) for item in items)
    lines = [f"• {item['name']}: {item['stock']} units" for item in items]
    header = f"{category.title()} Category – {len(items)} SKUs · {total_units} units"
    return header + "\n" + "\n".join(lines)


@function_tool
def inventory_search_items(query: str) -> str:
    """Search products by name (case-insensitive)."""
    raw_query = query.strip()
    is_customer = raw_query.lower().startswith("customer:")
    if is_customer:
        _, _, customer_query = raw_query.partition(":")
        search_term = customer_query.strip() or raw_query
    else:
        search_term = raw_query

    items = inventory_analytics_service.search_items(search_term)
    if not items:
        return f"No inventory matches for '{search_term}'."

    if is_customer:
        lines = []
        for item in items:
            name = item['name']
            category = item['category']
            price = item.get('price')
            if price:
                lines.append(f"• {name} ({category}) - PKR {price:,}")
            else:
                lines.append(f"• {name} ({category}) - Price on request")
        return "🛍️ Matching Products\n" + "\n".join(lines)

    lines = [
        f"• {item['name']} ({item['category']}): {item['stock']} in stock, {item['incoming']} incoming"
        for item in items
    ]
    return "🔍 Matching Products\n" + "\n".join(lines)


@function_tool
def inventory_customer_catalog(limit: int = 6) -> str:
    """Customer-safe catalog with product names and prices (no stock counts)."""
    items = inventory_analytics_service.get_all_items(limit=limit)
    if not items:
        return "Our catalog is empty right now. Check back soon!"

    lines = []
    for item in items:
        name = item['name']
        category = item['category']
        price = item.get('price')
        if price:
            lines.append(f"• {name} ({category}) - PKR {price:,}")
        else:
            lines.append(f"• {name} ({category}) - Price on request")
    
    return "🛍️ Available Products\n" + "\n".join(lines)
