"""
Example: Creating a post with an image from local file

This example demonstrates how to create a post with an image
by uploading a local image file.
"""

import sys
from pathlib import Path

# Add src to path (for development)
sys.path.insert(0, str(Path(__file__).parent.parent))

from src import FacebookManager, ImagePostRequest
from src.exceptions import PostCreationError, ImageUploadError, InvalidCredentialsError


def main():
    """Main function to create an image post from local file"""
    
    print("=" * 60)
    print("Facebook Manager - Image Post (File) Example")
    print("=" * 60)
    
    try:
        # Initialize the Facebook Manager
        print("\n[1/4] Initializing Facebook Manager...")
        manager = FacebookManager()
        print("✓ Manager initialized successfully")
        
        # Verify credentials
        print("\n[2/4] Verifying credentials...")
        manager.verify_credentials()
        print("✓ Credentials verified")
        
        # Get image path from user
        print("\n[3/4] Preparing image file...")
        
        # You can modify this to point to your image file
        # For this example, we'll check if a sample image exists
        sample_image_path = Path(__file__).parent / "sample_image.jpg"
        
        if not sample_image_path.exists():
            print(f"\n⚠️  Sample image not found at: {sample_image_path}")
            print("\nPlease provide the path to your image file:")
            user_path = input("Image path: ").strip()
            
            if not user_path:
                print("❌ No path provided. Exiting.")
                sys.exit(1)
            
            image_path = Path(user_path)
            
            if not image_path.exists():
                print(f"❌ Image not found at: {image_path}")
                sys.exit(1)
        else:
            image_path = sample_image_path
        
        print(f"✓ Using image: {image_path}")
        
        # Create an image post from file
        print("\n[4/4] Creating image post from file...")
        
        post_request = ImagePostRequest(
            message="📸 Photo of the day! \n\n"
                   "Uploaded via Facebook Manager Tool - "
                   "demonstrating file-based image posting.",
            image_path=str(image_path)
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
        print("\nCommon issues:")
        print("  - File doesn't exist")
        print("  - Invalid image format (supported: jpg, png, gif, bmp, webp)")
        print("  - File is corrupted")
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
