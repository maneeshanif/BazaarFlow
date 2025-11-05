"""
Real integration test - Tests actual Facebook API posting
WARNING: This will create real posts on your Facebook page!
Only run this when you're ready to test with real credentials.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src import FacebookManager, TextPostRequest, ImagePostRequest
from src.exceptions import FacebookAPIError, InvalidCredentialsError


def test_real_text_post():
    """Test creating a real text post"""
    print("\n" + "="*60)
    print("REAL INTEGRATION TEST - Text Post")
    print("="*60)
    
    try:
        with FacebookManager() as manager:
            print("\n[1/3] Verifying credentials...")
            manager.verify_credentials()
            print("✓ Credentials verified")
            
            print("\n[2/3] Creating text post...")
            post = TextPostRequest(
                message="🧪 Integration Test Post\n\n"
                       "This is an automated test post from the Facebook Manager Tool. "
                       "Testing text posting functionality."
            )
            
            response = manager.create_text_post(post)
            print(f"✓ Post created successfully!")
            print(f"   Post ID: {response.post_id}")
            
            print("\n[3/3] Retrieving post details...")
            post_data = manager.get_post(response.post_id)
            print(f"✓ Post retrieved:")
            print(f"   URL: {post_data.get('permalink_url', 'N/A')}")
            print(f"   Created: {post_data.get('created_time', 'N/A')}")
            
            print("\n" + "="*60)
            print("✅ TEXT POST TEST PASSED!")
            print("="*60)
            return True
            
    except InvalidCredentialsError as e:
        print(f"\n❌ AUTHENTICATION ERROR: {e}")
        print("\nPlease check your .env file:")
        print("  - FACEBOOK_PAGE_ID")
        print("  - FACEBOOK_ACCESS_TOKEN")
        return False
        
    except FacebookAPIError as e:
        print(f"\n❌ API ERROR: {e}")
        return False
        
    except Exception as e:
        print(f"\n❌ UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_real_image_post():
    """Test creating a real image post from URL"""
    print("\n" + "="*60)
    print("REAL INTEGRATION TEST - Image Post (URL)")
    print("="*60)
    
    try:
        with FacebookManager() as manager:
            print("\n[1/2] Creating image post from URL...")
            
            # Using a public sample image
            post = ImagePostRequest(
                message="🖼️ Integration Test - Image Post\n\n"
                       "Testing image posting functionality with URL-based upload.",
                image_url="https://picsum.photos/1200/630"
            )
            
            response = manager.create_image_post(post)
            print(f"✓ Image post created successfully!")
            print(f"   Post ID: {response.post_id}")
            
            print("\n[2/2] Post is now live on your Facebook page")
            
            print("\n" + "="*60)
            print("✅ IMAGE POST TEST PASSED!")
            print("="*60)
            return True
            
    except FacebookAPIError as e:
        print(f"\n❌ API ERROR: {e}")
        return False
        
    except Exception as e:
        print(f"\n❌ UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all integration tests"""
    print("\n" + "="*60)
    print("FACEBOOK MANAGER - REAL INTEGRATION TESTS")
    print("="*60)
    print("\n⚠️  WARNING: This will create REAL posts on your Facebook page!")
    print("\nMake sure you have:")
    print("  1. Valid credentials in .env file")
    print("  2. Confirmed you want to create test posts")
    
    response = input("\nDo you want to continue? (yes/no): ").strip().lower()
    
    if response != 'yes':
        print("\n❌ Tests cancelled by user.")
        sys.exit(0)
    
    # Run tests
    results = []
    
    results.append(("Text Post", test_real_text_post()))
    results.append(("Image Post (URL)", test_real_image_post()))
    
    # Summary
    print("\n\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    for name, passed in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{name}: {status}")
    
    all_passed = all(result[1] for result in results)
    
    if all_passed:
        print("\n🎉 All integration tests passed!")
        print("Your Facebook Manager Tool is working correctly!")
    else:
        print("\n⚠️  Some tests failed. Please review the errors above.")
    
    print("="*60)


if __name__ == "__main__":
    main()
