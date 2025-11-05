"""
Example: Retrieving and analyzing post comments

This example demonstrates how to:
1. Get all comments for a post
2. Extract keywords/topics from comments
3. Reply to specific comments
4. React to (like) comments
5. Hide or delete inappropriate comments
"""

import sys
from pathlib import Path

# Add src to path (for development)
sys.path.insert(0, str(Path(__file__).parent.parent))

from src import (
    FacebookManager,
    CommentReplyRequest,
    CommentReactionRequest
)
from src.exceptions import FacebookAPIError


def main():
    """Main function to demonstrate comment management"""
    
    print("=" * 70)
    print("Facebook Manager - Comment Analysis & Management Example")
    print("=" * 70)
    
    # Get post ID from user
    post_id = input("\nEnter the Post ID to analyze comments: ").strip()
    
    if not post_id:
        print("❌ No post ID provided. Exiting.")
        sys.exit(1)
    
    try:
        with FacebookManager() as manager:
            # ============================================================
            # 1. Retrieve Comments
            # ============================================================
            print("\n[1/5] Retrieving comments...")
            
            comments_response = manager.get_post_comments(
                post_id=post_id,
                limit=50  # Get up to 50 comments
            )
            
            print(f"✓ Retrieved {len(comments_response.comments)} comments")
            
            # Display comments
            print("\n" + "-" * 70)
            print("COMMENTS:")
            print("-" * 70)
            
            for i, comment in enumerate(comments_response.comments[:5], 1):
                print(f"\n{i}. From: {comment.from_user.get('name')}")
                print(f"   Message: {comment.message[:100]}...")
                print(f"   Likes: {comment.like_count} | Replies: {comment.comment_count}")
            
            if len(comments_response.comments) > 5:
                print(f"\n   ... and {len(comments_response.comments) - 5} more comments")
            
            # ============================================================
            # 1b. Extract Keywords from Comments
            # ============================================================
            print("\n" + "-" * 70)
            print("EXTRACTING KEYWORDS/TOPICS:")
            print("-" * 70)
            
            keywords = manager.extract_keywords(
                comments=comments_response.comments,
                top_n=15
            )
            
            for keyword, freq in keywords[:10]:
                bar = "█" * min(freq, 20)
                print(f"  {keyword:20s} [{freq:3d}] {bar}")
            
            # ============================================================
            # 2. Reply to a Comment
            # ============================================================
            print("\n[2/5] Reply to a comment...")
            
            if comments_response.comments:
                first_comment = comments_response.comments[0]
                print(f"\nReplying to comment from: {first_comment.from_user.get('name')}")
                print(f"Original comment: {first_comment.message[:50]}...")
                
                reply = input("\nEnter your reply (or press Enter to skip): ").strip()
                
                if reply:
                    reply_request = CommentReplyRequest(
                        comment_id=first_comment.comment_id,
                        message=reply
                    )
                    
                    response = manager.reply_to_comment(reply_request)
                    print(f"✓ {response.message}")
                else:
                    print("⊘ Skipped replying to comment")
            
            # ============================================================
            # 3. React to a Comment
            # ============================================================
            print("\n[3/5] React to a comment...")
            
            if comments_response.comments and len(comments_response.comments) > 1:
                second_comment = comments_response.comments[1]
                print(f"\nReacting to comment from: {second_comment.from_user.get('name')}")
                
                react = input("\nReact with LIKE? (yes/no): ").strip().lower()
                
                if react == 'yes':
                    reaction_request = CommentReactionRequest(
                        comment_id=second_comment.comment_id
                    )
                    
                    response = manager.react_to_comment(reaction_request)
                    print(f"✓ {response.message}")
                else:
                    print("⊘ Skipped reacting to comment")
            
            # ============================================================
            # 4. Hide a Comment (Optional)
            # ============================================================
            print("\n[4/5] Hide a comment...")
            
            hide_demo = input("\nDo you want to demo hiding a comment? (yes/no): ").strip().lower()
            
            if hide_demo == 'yes' and comments_response.comments:
                comment_to_hide = comments_response.comments[0]
                print(f"\nHiding comment from: {comment_to_hide.from_user.get('name')}")
                
                confirm = input("Confirm hide? (yes/no): ").strip().lower()
                
                if confirm == 'yes':
                    response = manager.hide_comment(comment_to_hide.comment_id)
                    print(f"✓ {response.message}")
                    print("Note: The comment is still visible to the commenter and their friends")
                else:
                    print("⊘ Cancelled hiding comment")
            else:
                print("⊘ Skipped hiding comment")
            
            # ============================================================
            # 5. Delete a Comment (Optional - Use with Caution!)
            # ============================================================
            print("\n[5/5] Delete a comment...")
            
            delete_demo = input("\n⚠️  Do you want to demo deleting a comment? (yes/no): ").strip().lower()
            
            if delete_demo == 'yes' and comments_response.comments:
                print("\n⚠️  WARNING: This will PERMANENTLY delete the comment!")
                comment_to_delete = comments_response.comments[0]
                print(f"Comment from: {comment_to_delete.from_user.get('name')}")
                print(f"Message: {comment_to_delete.message[:100]}")
                
                confirm = input("\n⚠️  Type 'DELETE' to confirm: ").strip()
                
                if confirm == 'DELETE':
                    response = manager.delete_comment(comment_to_delete.comment_id)
                    print(f"✓ {response.message}")
                else:
                    print("⊘ Cancelled deleting comment")
            else:
                print("⊘ Skipped deleting comment")
            
            print("\n" + "=" * 70)
            print("✅ Comment management demo completed!")
            print("=" * 70)
            
    except FacebookAPIError as e:
        print(f"\n❌ Facebook API Error: {e}")
        sys.exit(1)
        
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
