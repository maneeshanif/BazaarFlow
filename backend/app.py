# --------------------------------------------------------------
# app.py   –   WhatsApp Sales Agent (FastAPI + pywa_async + Gemini)
# --------------------------------------------------------------

"""
BazaarFlow FastAPI Backend
Integrates WhatsApp API with Sales Agent for automated customer interactions.
"""

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import PlainTextResponse, JSONResponse
from pywa_async import WhatsApp, filters
from pywa_async.types import Message
from contextlib import asynccontextmanager
from my_agents.sales_agent import sales_agent
from agents import Runner, SQLiteSession
import json
from controllers.sales_controller import router as sales_router
from controllers.chat_controller import router as chat_router
from dotenv import load_dotenv, find_dotenv
import os

# Load environment from repository root (find parent .env)
load_dotenv(find_dotenv())

# Import custom logger utility
from utils.logger import setup_logger, log_webhook_event, log_message_event
from wa_client import init_wa

# Set up application logger
logger = setup_logger(__name__)
 
# -------------------------- Initialize Core Components ---------------------------

# Helper: safe int conversion
def safe_int(value: str | None) -> int | None:
    if not value:
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        return None

@asynccontextmanager
async def lifespan(app: FastAPI):
# ---- startup ------------------------------------------------
    try:
        log_webhook_event(logger, "startup_begin")
        
        # Validate required environment variables
        required_vars = ['WA_TOKEN', 'WA_APP_ID', 'WA_APP_SECRET', 'WA_PHONE_ID']
        missing_vars = [var for var in required_vars if not os.getenv(var)]
        if missing_vars:
            log_webhook_event(logger, "startup_error", {
                "error": "missing_env_vars",
                "missing": missing_vars
            })
            raise ValueError(f"Missing required environment variables: {missing_vars}")

        # Attempt to register webhook
        webhook_url = os.getenv("WA_CALLBACK_URL", "https://planiform-doctrinally-lynnette.ngrok-free.dev/")
        log_webhook_event(logger, "webhook_registration", {
            "url": webhook_url
        })
            
        resp = await wa.send_message(
            to=os.getenv("WA_ADMIN_PHONE", "923012177654"),
            text="👋 Welcome to BazaFlow! 🚀 Let's talk about your products and business goals 💡",
        )

        # resp = await wa.send_template(
        #     to="923012177654",
        #     name="buy_new_iphone_x",
        #     language=TemplateLanguage.ENGLISH_US,
        #     params=[
        #         {"type": "header", "parameters": [{"type": "text", "text": "15"}]},
        #         {"type": "body", "parameters": [
        #             {"type": "text", "text": "WA_IPHONE_15"},
        #             {"type": "text", "text": "15"}
        #         ]}
        #     ]
        # )

        print("Startup send success:", resp.id)
    except Exception as e:
        print("Startup send error:", e)
    yield
    # ---- shutdown -----------------------------------------------
    print("App shutdown – cleaning up...")


# Create FastAPI app with lifespan (pywa requires server instance at init time)
fastapi_app = FastAPI(
    title="BazaarFlow API",
    description="BazaarFlow backend API with WhatsApp integration",
    version="1.0.0",
    lifespan=lifespan,
)

# Include MVC-style routes
fastapi_app.include_router(sales_router, prefix="/api")
fastapi_app.include_router(chat_router, prefix="/api")

# Initialize WhatsApp client using helper module (this registers /webhook routes)
wa = init_wa(fastapi_app, logger)

# Log registered routes for debugging
for route in fastapi_app.routes:
    logger.info(f"Registered route: {route.path} [{route.methods}]")

# --- CORS middleware -----------------------------------------
from fastapi.middleware.cors import CORSMiddleware

allowed_origins = [
    os.getenv("FRONTEND_ORIGIN", "http://localhost:3000"),
    "http://127.0.0.1:3000",
]

fastapi_app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins if os.getenv("PRODUCTION") else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)



# -------------------------- Session store ----------------------
user_sessions: dict[str, SQLiteSession] = {}


# Updated Handler: SDK Runner with SQLiteSession

# Enhanced error handling for message processing
@wa.on_message(filters.text)
async def handle_incoming_message(client: WhatsApp, msg: Message):
    user_id = msg.from_user.wa_id
    
    # Log message received
    log_message_event(logger, "received", user_id, {
        "text_length": len(msg.text),
        "timestamp": msg.date.isoformat()
    })

    try:
        # Get or create SQLiteSession (built-in memory)
        if user_id not in user_sessions:
            # SDK creates DB at 'sessions.db' – per-user table
            session = SQLiteSession(session_id=user_id)  # Per-user DB for isolation
            user_sessions[user_id] = session
            log_message_event(logger, "session_created", user_id)
        
        session = user_sessions[user_id]
        log_message_event(logger, "processing", user_id, {"session_id": session.session_id})

        # Run agent with Runner (handles loop, tools, memory)
        response = await Runner.run(
            starting_agent=sales_agent,
            input=msg.text,
            session=session,  # Built-in session for history
        )

        # Extract output (SDK response)
        response_text = response.final_output if hasattr(response, 'final_output') else str(response)

        # Reply to user
        reply = await msg.reply_text(response_text)
        log_message_event(logger, "reply_sent", user_id, {
            "reply_id": reply.id,
            "response_length": len(response_text)
        })
        await msg.react("✅")

    except Exception as e:
        # Log error with context and full traceback
        log_message_event(logger, "error", user_id, {
            "error": str(e),
            "message": msg.text
        })
        logger.error("Message handling error", exc_info=True)
        
        # Send user-friendly error response
        error_reply = "Sorry, I'm experiencing technical difficulties. Please try again in a moment or contact support."
        try:
            await msg.reply_text(error_reply)
            log_message_event(logger, "error_response_sent", user_id)
        except Exception as reply_error:
            log_message_event(logger, "error_response_failed", user_id, {
                "error": str(reply_error)
            })
            logger.error("Failed to send error message", exc_info=True)


# -------------------------- Health / Ready --------------------
@fastapi_app.get("/health", response_class=JSONResponse)
async def health():
    """Lightweight liveness endpoint for probes and quick checks.

    Returns 200 JSON `{"status": "ok"}` when the app is up. Keep this
    intentionally fast and side-effect free so load-balancers and health
    monitoring can hit it frequently without triggering external APIs.
    """
    return JSONResponse(status_code=200, content={"status": "ok"})

@fastapi_app.get("/webhook/status", response_class=JSONResponse)
async def webhook_status():
    """Check WhatsApp webhook registration status and configuration."""
    try:
        # Check environment variables
        required_vars = ['WA_TOKEN', 'WA_APP_ID', 'WA_APP_SECRET', 'WA_PHONE_ID']
        env_status = {var: bool(os.getenv(var)) for var in required_vars}
        
        # Get current webhook URL
        webhook_url = os.getenv("WA_CALLBACK_URL", "https://planiform-doctrinally-lynnette.ngrok-free.dev/")
        webhook_endpoint = os.getenv("WA_WEBHOOK_ENDPOINT", "/webhook")
        full_webhook_url = f"{webhook_url.rstrip('/')}{webhook_endpoint}"
        
        # Check registered routes
        webhook_routes = [
            {"path": route.path, "methods": list(route.methods)}
            for route in fastapi_app.routes 
            if route.path.startswith(webhook_endpoint)
        ]

        status_info = {
            "status": "ok",
            "environment_variables": env_status,
            "webhook_url": full_webhook_url,
            "registered_routes": webhook_routes,
            "validate_updates": os.getenv("WA_VALIDATE_UPDATES", "false").lower() in ("1","true","yes"),
        }
        
        log_webhook_event(logger, "status_check", status_info)
        return JSONResponse(status_code=200, content=status_info)
        
    except Exception as e:
        logger.error("[WhatsApp] Error checking webhook status", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)}
        )
