# BazaarFlow — Full Folder Structure

```
BazaarFlow/
│
├── 📁 app/                                ← 🐍 Main FastAPI Backend
│   │
│   ├── 📄 main.py                         ← App entry point
│   ├── 📄 runner.py                       ← CLI task runner
│   │
│   ├── 📁 api/                            ← HTTP API Layer
│   │   ├── 📁 routers/                    ← Route definitions
│   │   │   ├── 📄 main_router.py          ← Aggregates all routers
│   │   │   ├── 📄 auth_router.py
│   │   │   ├── 📄 chat_router.py
│   │   │   ├── 📄 inventory_router.py
│   │   │   ├── 📄 marketing_router.py
│   │   │   ├── 📄 sales_router.py
│   │   │   ├── 📄 support_router.py
│   │   │   ├── 📄 vendors_router.py
│   │   │   ├── 📄 webhook_router.py
│   │   │   ├── 📄 logs_router.py
│   │   │   └── 📁 v1/                    ← Versioned routes
│   │   │
│   │   └── 📁 controllers/               ← Business logic per route
│   │       ├── 📄 auth_controller.py
│   │       ├── 📄 chat_controller.py
│   │       ├── 📄 inventory_controller.py
│   │       ├── 📄 marketing_controller.py
│   │       ├── 📄 sales_controller.py
│   │       ├── 📄 support_controller.py
│   │       ├── 📄 vendors_controller.py
│   │       ├── 📄 webhook_controller.py
│   │       └── 📄 logs_controller.py
│   │
│   ├── 📁 agents/                         ← 🤖 AI Agents (LLM-powered)
│   │   ├── 📄 config.py                   ← Agent config & model selection
│   │   ├── 📄 model.py                    ← LLM model definition
│   │   ├── 📄 marketing_agent.py
│   │   ├── 📄 sales_agent.py
│   │   ├── 📄 inventory_agent.py
│   │   ├── 📄 finance_agent.py
│   │   └── 📁 tools/                      ← Tools available to agents
│   │       ├── 📄 marketing_tool.py
│   │       ├── 📄 inventory_tool.py
│   │       ├── 📄 sales_tool.py
│   │       └── 📄 finance_tool.py
│   │
│   ├── 📁 services/                       ← ⚙️ Core Business Services
│   │   ├── 📄 marketing_service.py        ← 📣 Biggest file (48KB)
│   │   ├── 📄 marketing_scheduler.py      ← Post scheduling / cron
│   │   ├── 📄 inventory_service.py
│   │   ├── 📄 finance_service.py
│   │   ├── 📄 sales_service.py
│   │   ├── 📄 chat_service.py
│   │   ├── 📄 vapi_support_service.py     ← Voice AI support
│   │   └── 📄 whatsapp.py                 ← WhatsApp integration
│   │
│   ├── 📁 integrations/                   ← 🔌 External Platform SDKs
│   │   ├── 📄 facebook_manager.py         ← FB Graph API wrapper (40KB)
│   │   ├── 📄 fb.py                       ← FB helpers (14KB)
│   │   ├── 📄 fb_config.py                ← FB app credentials
│   │   └── 📄 fb_model.py                 ← FB data models
│   │
│   ├── 📁 models/                         ← 🗃️ SQLAlchemy ORM Models
│   │   ├── 📄 __init__.py                 ← Exports all models
│   │   ├── 📄 common.py                   ← Base model / shared fields
│   │   ├── 📄 user.py
│   │   ├── 📄 customer.py
│   │   ├── 📄 vendor.py
│   │   ├── 📄 inventory.py
│   │   ├── 📄 order.py
│   │   ├── 📄 message.py
│   │   ├── 📄 marketing.py
│   │   ├── 📄 facebook.py
│   │   └── 📄 support.py
│   │
│   ├── 📁 schemas/                        ← 📋 Pydantic Request/Response
│   │   ├── 📄 common.py
│   │   ├── 📄 user.py
│   │   ├── 📄 customer.py
│   │   ├── 📄 vendor.py
│   │   ├── 📄 inventory.py
│   │   ├── 📄 order.py
│   │   ├── 📄 marketing.py
│   │   ├── 📄 facebook.py
│   │   └── 📄 support.py
│   │
│   ├── 📁 crud/                           ← 🛠️ Raw DB Operations
│   │   ├── 📄 crud_user.py
│   │   ├── 📄 crud_customer.py
│   │   ├── 📄 crud_vendor.py
│   │   ├── 📄 crud_inventory.py
│   │   ├── 📄 crud_order.py
│   │   ├── 📄 crud_marketing.py
│   │   ├── 📄 crud_message.py
│   │   └── 📄 crud_support.py
│   │
│   ├── 📁 repositories/                   ← 📦 Data Access Patterns
│   │   ├── 📄 repository.py               ← Generic base repository
│   │   ├── 📄 user_repository.py
│   │   ├── 📄 marketing_repository.py
│   │   ├── 📄 marketing_scheduled_repository.py
│   │   └── 📄 json_store.py               ← JSON flat-file store
│   │
│   ├── 📁 db/                             ← 🗄️ Database Setup
│   │   ├── 📄 database.py                 ← SQLAlchemy engine & session
│   │   ├── 📄 database_ro.py              ← Read-only session
│   │   └── 📄 dependencies.py             ← FastAPI DB dependency
│   │
│   ├── 📁 core/                           ← 🔐 Cross-cutting Concerns
│   │   ├── 📄 settings.py                 ← App config (env vars)
│   │   ├── 📄 security.py                 ← JWT auth / password hashing
│   │   ├── 📄 exceptions.py               ← Custom HTTP exceptions
│   │   └── 📄 dependencies.py             ← Shared FastAPI deps
│   │
│   ├── 📁 middleware/                     ← 🔁 HTTP Middleware
│   │   ├── 📄 rate_limiter.py
│   │   └── 📄 request_logger.py
│   │
│   ├── 📁 prompts/                        ← 🧠 LLM System Prompts
│   │   ├── 📁 marketing/
│   │   ├── 📁 inventory/
│   │   ├── 📁 sales/
│   │   └── 📁 finance/
│   │
│   ├── 📁 mcp_server/                     ← 🔧 Model Context Protocol
│   │   ├── 📄 server.py
│   │   └── 📄 test_server.py
│   │
│   ├── 📁 utils/                          ← 🧰 Shared Utilities
│   │   ├── 📄 logger.py
│   │   ├── 📄 live_logs.py                ← Real-time log streaming
│   │   ├── 📄 streaming.py                ← SSE / streaming responses
│   │   ├── 📄 agent_hooks.py              ← Agent lifecycle hooks
│   │   └── 📄 diagnose.py                 ← System diagnostics
│   │
│   └── 📁 data/                           ← 📂 JSON Flat-file Cache
│       ├── 📄 users.json
│       ├── 📄 customers.json
│       ├── 📄 vendors.json
│       ├── 📄 messages.json
│       ├── 📄 marketing_posts.json
│       ├── 📄 marketing_schedules.json
│       ├── 📄 marketing_scheduled_posts.json
│       ├── 📄 marketing_scheduled_campaigns.json
│       ├── 📄 marketing_comment_replies.json
│       └── 📄 facebook_accounts.json
│
├── 📁 frontend/                           ← ⚛️ Next.js 14 (App Router)
│   │
│   ├── 📁 app/                            ← Pages & Routes
│   │   ├── 📄 page.tsx                    ← 🏠 Landing Page
│   │   ├── 📄 layout.tsx                  ← Root Layout
│   │   ├── 📄 global.css
│   │   │
│   │   ├── 📁 sign-in/                    ← Auth: Login
│   │   ├── 📁 register/                   ← Auth: Register
│   │   │
│   │   ├── 📁 dashboard/                  ← Main App Dashboard
│   │   │   ├── 📄 page.tsx                ← Dashboard Home
│   │   │   │
│   │   │   ├── 📁 inventory/              ← Inventory Management
│   │   │   ├── 📁 orders/                 ← Orders Management
│   │   │   ├── 📁 sales/                  ← Sales Analytics
│   │   │   │
│   │   │   ├── 📁 marketing/              ← 📣 Marketing Hub
│   │   │   │   ├── 📄 MarketingContext.tsx ← Global state (43KB)
│   │   │   │   ├── 📄 layout.tsx
│   │   │   │   ├── 📁 overview/           ← Marketing overview
│   │   │   │   ├── 📁 studio/             ← Post creator/editor
│   │   │   │   ├── 📁 schedule/           ← Post scheduler
│   │   │   │   ├── 📁 activity/           ← Activity feed
│   │   │   │   ├── 📁 insights/           ← Analytics & insights
│   │   │   │   ├── 📁 credentials/        ← FB/social credentials
│   │   │   │   └── 📁 settings/
│   │   │   │
│   │   │   ├── 📁 support/                ← Customer Support (VAPI)
│   │   │   └── 📁 settings/               ← Account Settings
│   │   │
│   │   ├── 📁 agents/                     ← AI Agents UI
│   │   ├── 📁 chat/                       ← Chat Interface
│   │   ├── 📁 logs/                       ← System Logs Viewer
│   │   ├── 📁 demo/                       ← Demo / Onboarding
│   │   ├── 📁 about/
│   │   ├── 📁 contact/
│   │   └── 📁 api/                        ← Next.js API Routes
│   │
│   ├── 📁 components/                     ← Reusable Components
│   │   ├── 📄 DashboardSidebar.tsx
│   │   ├── 📄 OrderCard.tsx
│   │   ├── 📄 MeridianCards.tsx
│   │   ├── 📄 ThemeToggle.tsx
│   │   ├── 📄 OfflineBanner.tsx
│   │   ├── 📄 SmoothScroll.tsx
│   │   ├── 📁 sales/                      ← Sales-specific components
│   │   └── 📁 ui/                         ← shadcn/ui base components
│   │
│   ├── 📁 hooks/                          ← Custom React Hooks
│   │   ├── 📄 use-toast.ts
│   │   ├── 📄 use-mobile.tsx
│   │   └── 📄 use-local-storage.ts
│   │
│   ├── 📁 lib/                            ← Shared Utilities
│   │   ├── 📄 utils.ts                    ← cn() helper
│   │   └── 📄 ws.ts                       ← WebSocket client
│   │
│   └── 📁 public/                         ← Static Assets
│
├── 📁 alembic/                            ← 🗄️ DB Migrations
│   ├── 📄 env.py
│   ├── 📄 script.py.mako
│   └── 📁 versions/                       ← Migration scripts
│
├── 📁 tests/                              ← 🧪 Test Suite
├── 📁 docs/                               ← 📚 Documentation
├── 📄 dev.db                              ← SQLite Dev Database
├── 📄 docker-compose.yml
├── 📄 backend.Dockerfile
├── 📄 pyproject.toml
└── 📄 .env
```
