"""
Example: Using Facebook Manager with context manager

This example demonstrates best practices for using the FacebookManager
with Python's context manager protocol.
"""

import sys
from pathlib import Path

# Add src to path (for development)
sys.path.insert(0, str(Path(__file__).parent.parent))

from src import FacebookManager, TextPostRequest, ImagePostRequest


def main():
    """Main function demonstrating context manager usage"""
    
    print("=" * 60)
    print("Facebook Manager - Context Manager Example")
    print("=" * 60)
    
    # Using context manager ensures proper cleanup
    with FacebookManager() as manager:
        print("\n✓ Manager initialized (context manager)")
        
        # Verify credentials
        print("\nVerifying credentials...")
        if manager.verify_credentials():
            print("✓ Credentials verified")
        
        # Example 1: Text post
        print("\n[Example 1] Creating text post...")
        try:
            text_post = TextPostRequest(
                message="Testing context manager pattern 🔧"
            )
            response = manager.create_text_post(text_post)
            print(f"✓ Text post created: {response.post_id}")
        except Exception as e:
            print(f"❌ Text post failed: {e}")
        
        # Example 2: Image post
        print("\n[Example 2] Creating image post...")
        try:
            image_post = ImagePostRequest(
                message="Image post using context manager 📷",
                image_url="https://picsum.photos/800/600"
            )
            response = manager.create_image_post(image_post)
            print(f"✓ Image post created: {response.post_id}")
        except Exception as e:
            print(f"❌ Image post failed: {e}")
    
    # Manager is automatically closed here
    print("\n✓ Manager closed automatically")
    
    print("\n" + "=" * 60)
    print("Context manager example completed successfully!")
    print("=" * 60)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)
