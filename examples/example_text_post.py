"""
Example: Creating a simple text post on Facebook

This example demonstrates how to create a basic text post
using the Facebook Manager Tool.
"""

import sys
from pathlib import Path

# Add src to path (for development)
sys.path.insert(0, str(Path(__file__).parent.parent))

from src import FacebookManager, TextPostRequest
from src.exceptions import PostCreationError, InvalidCredentialsError


def main():
    """Main function to create a text post"""
    
    print("=" * 60)
    print("Facebook Manager - Text Post Example")
    print("=" * 60)
    
    try:
        # Initialize the Facebook Manager
        # It will automatically load credentials from .env file
        print("\n[1/3] Initializing Facebook Manager...")
        manager = FacebookManager()
        print("✓ Manager initialized successfully")
        
        # Verify credentials
        print("\n[2/3] Verifying credentials...")
        manager.verify_credentials()
        print("✓ Credentials verified")
        
        # Create a text post
        print("\n[3/3] Creating text post...")
        post_request = TextPostRequest(
            message="Hello from Facebook Manager Tool! 🚀\n\n"
                   "This is an automated post created using our "
                   "multi-agent system integration."
        )
        
        response = manager.create_text_post(post_request)
        
        print("✓ Post created successfully!")
        print(f"\nPost ID: {response.post_id}")
        print(f"Success: {response.success}")
        print(f"Message: {response.message}")
        
        # Retrieve post details
        print("\n[Bonus] Retrieving post details...")
        post_data = manager.get_post(response.post_id)
        print(f"Post URL: {post_data.get('permalink_url', 'N/A')}")
        print(f"Created: {post_data.get('created_time', 'N/A')}")
        
        print("\n" + "=" * 60)
        print("SUCCESS! Your post is now live on Facebook.")
        print("=" * 60)
        
    except InvalidCredentialsError as e:
        print(f"\n❌ Error: Invalid credentials")
        print(f"Details: {e}")
        print("\nPlease check your .env file and ensure:")
        print("  - FACEBOOK_PAGE_ID is correct")
        print("  - FACEBOOK_ACCESS_TOKEN is valid and not expired")
        sys.exit(1)
        
    except PostCreationError as e:
        print(f"\n❌ Error: Failed to create post")
        print(f"Details: {e}")
        sys.exit(1)
        
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)
    
    finally:
        # Clean up
        if 'manager' in locals():
            manager.close()


if __name__ == "__main__":
    main()
