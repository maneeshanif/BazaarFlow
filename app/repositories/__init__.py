"""Repositories package — re-exports from all sub-modules for backwards compatibility."""
from app.repositories.repository import (
    get_vendor_by_phone_number_id,
    get_vendor,
    upsert_vendor,
    update_vendor_settings,
    list_vendors,
    upsert_customer,
    list_customers,
    get_customer,
    record_message,
    list_messages,
    recent_messages,
)
from app.repositories.marketing_repository import (
    upsert_facebook_account,
    list_facebook_accounts,
    get_facebook_account,
    delete_facebook_account,
    save_schedule,
    get_schedule,
    list_schedules,
    mark_schedule_triggered,
    record_marketing_post,
    list_marketing_posts,
    update_post_insights,
    delete_marketing_post,
    record_comment_reply,
    get_comment_reply,
)
from app.repositories import marketing_repository
from app.repositories import marketing_scheduled_repository
from app.repositories import user_repository