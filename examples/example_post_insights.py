"""
Example: Get Post Insights and Analytics

This example demonstrates how to retrieve engagement metrics for a specific post,
including reach, impressions, reactions breakdown, and shares.
"""

import sys
import json
from pathlib import Path

# Add src to path (for development)
sys.path.insert(0, str(Path(__file__).parent.parent))

from src import FacebookManager, InsightPeriod
from src.exceptions import FacebookAPIError


def main():
    """Main function to demonstrate post insights retrieval"""
    
    print("=" * 70)
    print("Facebook Manager - Post Insights Example")
    print("=" * 70)
    
    # Get post ID from user
    post_id = input("\nEnter the Post ID to analyze: ").strip()
    
    if not post_id:
        print("❌ No post ID provided. Exiting.")
        sys.exit(1)
    
    try:
        with FacebookManager() as manager:
            # ============================================================
            # 1. Get 24-Hour Insights
            # ============================================================
            print("\n[1/2] Retrieving 24-hour insights...")
            
            insights_24h = manager.get_post_insights(
                post_id=post_id,
                period=InsightPeriod.LAST_24_HOURS
            )
            
            print("\n" + "=" * 70)
            print("📊 POST INSIGHTS - LAST 24 HOURS")
            print("=" * 70)
            
            print(f"\n📈 Reach & Impressions:")
            print(f"   Reach:        {insights_24h.reach:,} unique users")
            print(f"   Impressions:  {insights_24h.impressions:,} total views")
            
            print(f"\n❤️  Reactions Breakdown:")
            print(f"   👍 Like:      {insights_24h.reactions.like:,}")
            print(f"   ❤️  Love:      {insights_24h.reactions.love:,}")
            print(f"   😮 Wow:       {insights_24h.reactions.wow:,}")
            print(f"   😂 Haha:      {insights_24h.reactions.haha:,}")
            print(f"   😢 Sad:       {insights_24h.reactions.sad:,}")
            print(f"   😠 Angry:     {insights_24h.reactions.angry:,}")
            print(f"   🤗 Care:      {insights_24h.reactions.care:,}")
            print(f"   ─────────────────────")
            print(f"   ✨ TOTAL:     {insights_24h.reactions.total:,}")
            
            print(f"\n💬 Engagement:")
            print(f"   Comments:     {insights_24h.comments_count:,}")
            print(f"   Shares:       {insights_24h.shares_count:,}")
            print(f"   Clicks:       {insights_24h.clicked:,}")
            
            print(f"\n📊 Engagement Rate: {insights_24h.engagement_rate:.2f}%")
            
            # ============================================================
            # 2. Get 7-Day Insights
            # ============================================================
            print("\n[2/2] Retrieving 7-day insights...")
            
            insights_7d = manager.get_post_insights(
                post_id=post_id,
                period=InsightPeriod.LAST_7_DAYS
            )
            
            print("\n" + "=" * 70)
            print("📊 POST INSIGHTS - LAST 7 DAYS")
            print("=" * 70)
            
            print(f"\n📈 Reach & Impressions:")
            print(f"   Reach:        {insights_7d.reach:,} unique users")
            print(f"   Impressions:  {insights_7d.impressions:,} total views")
            
            print(f"\n❤️  Reactions Breakdown:")
            print(f"   👍 Like:      {insights_7d.reactions.like:,}")
            print(f"   ❤️  Love:      {insights_7d.reactions.love:,}")
            print(f"   😮 Wow:       {insights_7d.reactions.wow:,}")
            print(f"   😂 Haha:      {insights_7d.reactions.haha:,}")
            print(f"   😢 Sad:       {insights_7d.reactions.sad:,}")
            print(f"   😠 Angry:     {insights_7d.reactions.angry:,}")
            print(f"   🤗 Care:      {insights_7d.reactions.care:,}")
            print(f"   ─────────────────────")
            print(f"   ✨ TOTAL:     {insights_7d.reactions.total:,}")
            
            print(f"\n💬 Engagement:")
            print(f"   Comments:     {insights_7d.comments_count:,}")
            print(f"   Shares:       {insights_7d.shares_count:,}")
            print(f"   Clicks:       {insights_7d.clicked:,}")
            
            print(f"\n📊 Engagement Rate: {insights_7d.engagement_rate:.2f}%")
            
            # ============================================================
            # 3. Export as JSON
            # ============================================================
            print("\n" + "=" * 70)
            print("💾 JSON Export")
            print("=" * 70)
            
            export_json = input("\nExport insights as JSON? (yes/no): ").strip().lower()
            
            if export_json == 'yes':
                data = {
                    "post_id": post_id,
                    "insights_24h": insights_24h.model_dump(),
                    "insights_7d": insights_7d.model_dump()
                }
                
                filename = f"post_insights_{post_id.replace('_', '-')}.json"
                
                with open(filename, 'w') as f:
                    json.dump(data, f, indent=2)
                
                print(f"✓ Insights exported to: {filename}")
            
            # ============================================================
            # 4. Comparison Summary
            # ============================================================
            print("\n" + "=" * 70)
            print("📈 Growth Comparison (7 days vs 24 hours)")
            print("=" * 70)
            
            if insights_24h.reach > 0:
                reach_growth = ((insights_7d.reach - insights_24h.reach) / insights_24h.reach) * 100
                impressions_growth = ((insights_7d.impressions - insights_24h.impressions) / insights_24h.impressions) * 100
                
                print(f"\nReach Growth:        {reach_growth:+.1f}%")
                print(f"Impressions Growth:  {impressions_growth:+.1f}%")
            
            print("\n" + "=" * 70)
            print("✅ Post insights retrieval completed!")
            print("=" * 70)
            
    except FacebookAPIError as e:
        print(f"\n❌ Facebook API Error: {e}")
        print("\nNote: Make sure the post exists and you have permission to access insights.")
        sys.exit(1)
        
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
