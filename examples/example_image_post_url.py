"""
Example: Creating a post with an image from URL

This example demonstrates how to create a post with an image
using a public image URL.
"""

import sys
from pathlib import Path

# Add src to path (for development)
sys.path.insert(0, str(Path(__file__).parent.parent))

from src import FacebookManager, ImagePostRequest
from src.exceptions import PostCreationError, ImageUploadError, InvalidCredentialsError


def main():
    """Main function to create an image post from URL"""
    
    print("=" * 60)
    print("Facebook Manager - Image Post (URL) Example")
    print("=" * 60)
    
    try:
        # Initialize the Facebook Manager
        print("\n[1/3] Initializing Facebook Manager...")
        manager = FacebookManager()
        print("✓ Manager initialized successfully")
        
        # Verify credentials
        print("\n[2/3] Verifying credentials...")
        manager.verify_credentials()
        print("✓ Credentials verified")
        
        # Create an image post from URL
        print("\n[3/3] Creating image post from URL...")
        
        # Using a sample image from Picsum (Lorem Ipsum for photos)
        image_url = "https://picsum.photos/1200/630"
        
        post_request = ImagePostRequest(
            message="🖼️ Beautiful scenery! \n\n"
                   "Posted via Facebook Manager Tool - "
                   "demonstrating URL-based image posting.",
            image_url=image_url
        )
        
        response = manager.create_image_post(post_request)
        
        print("✓ Image post created successfully!")
        print(f"\nPost ID: {response.post_id}")
        print(f"Success: {response.success}")
        print(f"Message: {response.message}")
        
        print("\n" + "=" * 60)
        print("SUCCESS! Your image post is now live on Facebook.")
        print("=" * 60)
        
    except InvalidCredentialsError as e:
        print(f"\n❌ Error: Invalid credentials")
        print(f"Details: {e}")
        sys.exit(1)
        
    except ImageUploadError as e:
        print(f"\n❌ Error: Failed to upload image")
        print(f"Details: {e}")
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
