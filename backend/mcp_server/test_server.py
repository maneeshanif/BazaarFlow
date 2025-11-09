"""
Test script for BazaarFlow MCP Server tools
Run this to verify all tools are working correctly
"""

import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcp_server.server import (
    lookup_product, 
    list_all_products, 
    get_product_by_price_range, 
    get_product_by_category,
    PRODUCTS_DB
)


def test_lookup_product():
    """Test lookup_product tool"""
    print("\n=== Testing lookup_product ===")
    
    # Test valid queries
    test_queries = ["phone", "laptop", "tablet", "watch"]
    for query in test_queries:
        result = lookup_product(query)
        print(f"Query: '{query}' -> {result}")
    
    # Test invalid query
    result = lookup_product("invalid")
    print(f"Query: 'invalid' -> {result}")


def test_list_all_products():
    """Test list_all_products tool"""
    print("\n=== Testing list_all_products ===")
    result = list_all_products()
    print(result)


def test_get_product_by_price_range():
    """Test get_product_by_price_range tool"""
    print("\n=== Testing get_product_by_price_range ===")
    
    # Test various price ranges
    test_ranges = [
        (0, 800),
        (800, 1000),
        (1000, 2000),
        (2000, 3000),
    ]
    
    for min_price, max_price in test_ranges:
        result = get_product_by_price_range(min_price, max_price)
        print(f"\nPrice Range ${min_price}-${max_price}:")
        print(result)


def test_get_product_by_category():
    """Test get_product_by_category tool"""
    print("\n=== Testing get_product_by_category ===")
    
    # Test valid categories
    categories = ["mobile", "computer", "wearable"]
    for category in categories:
        result = get_product_by_category(category)
        print(f"\nCategory: '{category}'")
        print(result)
    
    # Test invalid category
    result = get_product_by_category("invalid")
    print(f"\nCategory: 'invalid'")
    print(result)


def test_products_db():
    """Verify PRODUCTS_DB structure"""
    print("\n=== Testing PRODUCTS_DB ===")
    print(f"Total products in database: {len(PRODUCTS_DB)}")
    print("\nProduct details:")
    for key, product in PRODUCTS_DB.items():
        print(f"  {key}: {product['name']} - ${product['price']} ({product['category']})")


def main():
    """Run all tests"""
    print("=" * 60)
    print("BazaarFlow MCP Server - Tool Testing")
    print("=" * 60)
    
    try:
        test_products_db()
        test_lookup_product()
        test_list_all_products()
        test_get_product_by_price_range()
        test_get_product_by_category()
        
        print("\n" + "=" * 60)
        print("✅ All tests completed successfully!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
