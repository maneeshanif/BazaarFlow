from app.core.settings import settings
"""Utility tools used by the marketing agent for data gathering."""

from __future__ import annotations

import json
import os
from collections import Counter
from typing import Any, Dict, List

import requests
from agents import function_tool

from app.services.inventory_service import inventory_analytics_service
from app.services.sales_service import list_orders

PEXELS_SEARCH_ENDPOINT = "https://api.pexels.com/v1/search"
_DEFAULT_PEXELS_TIMEOUT = 10


@function_tool
def marketing_inventory_snapshot(limit: int = 6) -> Dict[str, Any]:
    """Summarise top in-stock products and low-stock alerts for campaign angles."""

    detail = inventory_analytics_service.get_stock_health_detail()
    in_stock_items = list(detail.get("in_stock", {}).get("items", []))
    low_stock_items = list(detail.get("low_stock", {}).get("items", []))

    def _trim(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        subset = items[: max(limit, 0) or len(items)]
        output: List[Dict[str, Any]] = []
        for item in subset:
            output.append(
                {
                    "name": item.get("name"),
                    "stock": int(item.get("stock", 0)),
                    "incoming": int(item.get("incoming", 0)),
                }
            )
        return output

    restock = inventory_analytics_service.get_restock_queue(limit=limit)
    for candidate in restock:
        candidate["stock"] = int(candidate.get("stock", 0))
        candidate["reorder_point"] = int(candidate.get("reorder_point", 0))

    return {
        "in_stock_highlights": _trim(sorted(in_stock_items, key=lambda item: int(item.get("stock", 0)), reverse=True)),
        "low_stock_watchlist": _trim(low_stock_items),
        "restock_queue": restock,
    }


@function_tool
def marketing_sales_insights() -> Dict[str, Any]:
    """Aggregate recent orders for positioning guidance."""

    orders = list_orders()
    if not orders:
        return {
            "total_orders": 0,
            "top_products": [],
            "popular_keywords": [],
        }

    product_counter: Counter[str] = Counter()
    keyword_counter: Counter[str] = Counter()

    for order in orders:
        product_name = (order.get("product_name") or "").strip()
        if product_name:
            product_counter[product_name.lower()] += int(order.get("quantity", 1) or 1)
            for token in product_name.lower().split():
                keyword_counter[token] += 1

    top_products = [
        {
            "product_name": name.title(),
            "orders": count,
        }
        for name, count in product_counter.most_common(5)
    ]

    popular_keywords = [
        {
            "keyword": keyword,
            "mentions": mentions,
        }
        for keyword, mentions in keyword_counter.most_common(8)
    ]

    return {
        "total_orders": len(orders),
        "top_products": top_products,
        "popular_keywords": popular_keywords,
    }


@function_tool
def marketing_image_search(query: str, orientation: str = "square") -> Dict[str, Any]:
    """Look up a marketing-friendly image via the Pexels API."""

    api_key = settings.PEXELS_API_KEY
    if not api_key:
        return {
            "error": "PEXELS_API_KEY not configured",
            "query": query,
        }

    headers = {"Authorization": api_key}
    params = {"query": query, "per_page": 3, "orientation": orientation}
    try:
        response = requests.get(
            PEXELS_SEARCH_ENDPOINT,
            headers=headers,
            params=params,
            timeout=_DEFAULT_PEXELS_TIMEOUT,
        )
        response.raise_for_status()
        data: Dict[str, Any] = response.json()
    except (requests.RequestException, json.JSONDecodeError) as exc:
        return {
            "error": f"pexels_error: {exc}",
            "query": query,
        }

    photos: List[Dict[str, Any]] = data.get("photos", [])
    formatted: List[Dict[str, Any]] = []
    for photo in photos:
        src: Dict[str, Any] = photo.get("src", {})
        formatted.append(
            {
                "photographer": photo.get("photographer"),
                "url": photo.get("url"),
                "attribution": photo.get("photographer_url"),
                "image_url": src.get("medium") or src.get("large") or src.get("original"),
            }
        )

    return {
        "query": query,
        "results": formatted,
    }
