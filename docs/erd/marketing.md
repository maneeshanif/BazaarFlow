# Marketing — ERD

> Generated from the schema by `docs/erd/generate_erd.py`. Do not hand-edit the diagram;
> edit `marketing.template.md` for the prose.

Posts to the shop's Facebook Page, the schedule that drafts them, and the replies proposed for the comments they get.
Back to the [overview](overview.md).

```mermaid
erDiagram
    %% Marketing
    facebook_accounts {
        uuid id PK
        uuid tenant_id FK
        varchar_100 page_id
        varchar_255 page_name
        varchar_512 access_token
        timestamptz created_at
        timestamptz updated_at
    }
    marketing_posts {
        uuid id PK
        uuid tenant_id FK
        varchar_255 title
        text message
        text hashtags
        text image_url
        varchar_255 fb_post_id
        varchar_50 status
        timestamptz scheduled_for
        timestamptz published_at
        integer attempts
        varchar_500 last_error
        varchar_10 source
        timestamptz comments_checked_at
        timestamptz created_at
        timestamptz updated_at
    }
    scheduled_campaigns {
        uuid id PK
        uuid tenant_id FK
        varchar_255 title
        text message
        timestamptz scheduled_at
        varchar_50 status
        boolean triggered
        timestamptz created_at
        timestamptz updated_at
    }
    marketing_schedules {
        uuid id PK
        uuid tenant_id FK
        boolean enabled
        varchar_30 goal
        varchar_300 notes
        varchar_20 tone
        varchar_12 language
        integer posts_per_day
        time window_start
        time window_end
        varchar_10 approval_mode
        date last_generated_on
        timestamptz created_at
        timestamptz updated_at
    }
    comment_replies {
        uuid id PK
        uuid tenant_id FK
        uuid post_id FK
        varchar_255 fb_post_id
        varchar_255 fb_comment_id
        varchar_120 author
        text comment_text
        text reply_text
        varchar_10 status
        uuid action_id
        integer attempts
        varchar_500 last_error
        varchar_255 fb_reply_id
        timestamptz posted_at
        timestamptz created_at
        timestamptz updated_at
    }

    marketing_posts ||--o{ comment_replies : "post_id"
```

## Tables

| Table | One row is | Notes |
| --- | --- | --- |
| `marketing_posts` | A post, from draft to published | `status` runs draft, pending_approval, approved, queued, published, failed or cancelled. `source` says studio, schedule or automation. `fb_post_id` is set once it is on Facebook and is what stops a double post. `comments_checked_at` throttles reading its comments. |
| `marketing_schedules` | The shop's posting plan | One row per shop: goal, tone, language, posts per day, the daily window, and `approval_mode` (`manual` or `auto`). |
| `comment_replies` | A Facebook comment and the reply proposed for it | Unique per (shop, Facebook comment id). `status` runs proposed, approved, posted, skipped or failed. `fb_reply_id` is set once the reply is on Facebook. |
| `facebook_accounts` | A linked Facebook Page (legacy v1 link) | The Page id is globally unique: one Page connects to one shop. New connections use `tenant_integrations`. |
| `scheduled_campaigns` | A v1 scheduled campaign | Legacy; kept until the old routes are removed. |

## Unenforced relationships

| Column | Points at | Why there is no FK |
| --- | --- | --- |
| `marketing_posts.fb_post_id`, `comment_replies.fb_comment_id`, `comment_replies.fb_reply_id` | Facebook's own ids | They live outside our database. |
| `comment_replies.action_id` | `agent_actions.id` (the approval for this reply) | The approval lives in the AI context. |
| `comment_replies.fb_post_id` | A Facebook post | A copy of `marketing_posts.fb_post_id` taken when the comment was stored, so the row stays meaningful on its own. |

## Notable design choices

- **Publishing is idempotent.** A post whose `fb_post_id` is already set is never published again, even after a restart.
- **Replies reuse the posting approval mode.** `auto` queues a reply at once; `manual` files an approval. A shop with
  no schedule confirms every reply.
- **Comment text is data.** It is stored as plain text and shown as text; it is never an instruction to the AI.
