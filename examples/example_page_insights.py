"""
Example: Get Page-Level Insights and Analytics

This example demonstrates how to retrieve overall page performance metrics,
including page reach, impressions, engaged users, and follower count.
"""

import sys
import json
from pathlib import Path

# Add src to path (for development)
sys.path.insert(0, str(Path(__file__).parent.parent))

from src import FacebookManager, InsightPeriod
from src.exceptions import FacebookAPIError


def main():
    """Main function to demonstrate page insights retrieval"""
    
    print("=" * 70)
    print("Facebook Manager - Page Insights Example")
    print("=" * 70)
    
    try:
        with FacebookManager() as manager:
            # Verify credentials and get page info
            print("\n[1/3] Verifying credentials...")
            manager.verify_credentials()
            print("✓ Credentials verified")
            
            # ============================================================
            # 1. Get 24-Hour Page Insights
            # ============================================================
            print("\n[2/3] Retrieving 24-hour page insights...")
            
            page_insights_24h = manager.get_page_insights(
                period=InsightPeriod.DAY
            )
            
            print("\n" + "=" * 70)
            print("📊 PAGE INSIGHTS - LAST 24 HOURS")
            print("=" * 70)
            
            print(f"\n📈 Page Reach & Impressions:")
            print(f"   Page Impressions:    {page_insights_24h.page_impressions:,}")
            print(f"   Page Reach:          {page_insights_24h.page_reach:,}")
            print(f"   Page Views:          {page_insights_24h.page_views_total:,}")
            
            print(f"\n👥 Audience Engagement:")
            print(f"   Engaged Users:       {page_insights_24h.page_engaged_users:,}")
            print(f"   Post Engagements:    {page_insights_24h.page_post_engagements:,}")
            print(f"   Consumptions:        {page_insights_24h.page_consumptions:,}")
            
            print(f"\n📊 Page Community:")
            print(f"   Total Fans:          {page_insights_24h.page_fans:,}")
            print(f"   Fans Online:         {page_insights_24h.page_fans_online:,}")
            
            # Calculate engagement rate
            if page_insights_24h.page_reach > 0:
                engagement_rate_24h = (page_insights_24h.page_engaged_users / page_insights_24h.page_reach) * 100
                print(f"\n💡 Engagement Rate:     {engagement_rate_24h:.2f}%")
            
            # ============================================================
            # 2. Get 7-Day Page Insights
            # ============================================================
            print("\n[3/3] Retrieving 7-day page insights...")
            
            page_insights_7d = manager.get_page_insights(
                period=InsightPeriod.WEEK
            )
            
            print("\n" + "=" * 70)
            print("📊 PAGE INSIGHTS - LAST 7 DAYS")
            print("=" * 70)
            
            print(f"\n📈 Page Reach & Impressions:")
            print(f"   Page Impressions:    {page_insights_7d.page_impressions:,}")
            print(f"   Page Reach:          {page_insights_7d.page_reach:,}")
            print(f"   Page Views:          {page_insights_7d.page_views_total:,}")
            
            print(f"\n👥 Audience Engagement:")
            print(f"   Engaged Users:       {page_insights_7d.page_engaged_users:,}")
            print(f"   Post Engagements:    {page_insights_7d.page_post_engagements:,}")
            print(f"   Consumptions:        {page_insights_7d.page_consumptions:,}")
            
            print(f"\n📊 Page Community:")
            print(f"   Total Fans:          {page_insights_7d.page_fans:,}")
            print(f"   Fans Online:         {page_insights_7d.page_fans_online:,}")
            
            # Calculate engagement rate
            if page_insights_7d.page_reach > 0:
                engagement_rate_7d = (page_insights_7d.page_engaged_users / page_insights_7d.page_reach) * 100
                print(f"\n💡 Engagement Rate:     {engagement_rate_7d:.2f}%")
            
            # ============================================================
            # 3. Growth Analysis
            # ============================================================
            print("\n" + "=" * 70)
            print("📈 Growth Analysis (7 days vs 24 hours)")
            print("=" * 70)
            
            if page_insights_24h.page_reach > 0:
                reach_growth = ((page_insights_7d.page_reach - page_insights_24h.page_reach) / page_insights_24h.page_reach) * 100
                impressions_growth = ((page_insights_7d.page_impressions - page_insights_24h.page_impressions) / page_insights_24h.page_impressions) * 100
                engagement_growth = ((page_insights_7d.page_engaged_users - page_insights_24h.page_engaged_users) / page_insights_24h.page_engaged_users) * 100 if page_insights_24h.page_engaged_users > 0 else 0
                
                print(f"\nReach Growth:           {reach_growth:+.1f}%")
                print(f"Impressions Growth:     {impressions_growth:+.1f}%")
                print(f"Engaged Users Growth:   {engagement_growth:+.1f}%")
            
            # ============================================================
            # 4. Performance Summary
            # ============================================================
            print("\n" + "=" * 70)
            print("📊 Performance Summary")
            print("=" * 70)
            
            avg_impressions_per_day = page_insights_7d.page_impressions / 7
            avg_engaged_per_day = page_insights_7d.page_engaged_users / 7
            
            print(f"\nAverage Daily Metrics (Last 7 Days):")
            print(f"   Impressions/Day:     {avg_impressions_per_day:,.0f}")
            print(f"   Engaged Users/Day:   {avg_engaged_per_day:,.0f}")
            
            if page_insights_7d.page_fans > 0:
                fan_engagement_rate = (page_insights_7d.page_engaged_users / page_insights_7d.page_fans) * 100
                print(f"   Fan Engagement Rate: {fan_engagement_rate:.2f}%")
            
            # ============================================================
            # 5. Export as JSON
            # ============================================================
            print("\n" + "=" * 70)
            print("💾 JSON Export")
            print("=" * 70)
            
            export_json = input("\nExport page insights as JSON? (yes/no): ").strip().lower()
            
            if export_json == 'yes':
                data = {
                    "page_id": page_insights_24h.page_id,
                    "insights_24h": page_insights_24h.model_dump(),
                    "insights_7d": page_insights_7d.model_dump(),
                    "analysis": {
                        "avg_impressions_per_day": round(avg_impressions_per_day, 2),
                        "avg_engaged_users_per_day": round(avg_engaged_per_day, 2)
                    }
                }
                
                filename = f"page_insights_{page_insights_24h.page_id}.json"
                
                with open(filename, 'w') as f:
                    json.dump(data, f, indent=2)
                
                print(f"✓ Page insights exported to: {filename}")
            
            print("\n" + "=" * 70)
            print("✅ Page insights retrieval completed!")
            print("=" * 70)
            
    except FacebookAPIError as e:
        print(f"\n❌ Facebook API Error: {e}")
        print("\nNote: Make sure you have 'read_insights' permission for your access token.")
        sys.exit(1)
        
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
