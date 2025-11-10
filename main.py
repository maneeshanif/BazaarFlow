try:
    from agents import Agent, Runner, OpenAIChatCompletionsModel, AsyncOpenAI, RunConfig
except Exception as _e:
    # Allow the module to be imported for tests/environments that don't have the
    # OpenAI Agent SDK available. The runtime will skip agent execution if the
    # SDK is missing.
    Agent = Runner = OpenAIChatCompletionsModel = AsyncOpenAI = RunConfig = None
    print("Warning: OpenAI Agent SDK not available - agent features disabled (", _e, ")")

import os
import sqlite3
try:
    from fastapi import FastAPI, HTTPException
    app = FastAPI(title="Finance Agent API")
except Exception:
    # FastAPI isn't installed in this environment (tests). Provide a minimal
    # dummy `app` that supplies no-op decorators so endpoints can be defined
    # and the module can be imported for unit tests.
    class _DummyApp:
        def on_event(self, _):
            def _deco(f):
                return f
            return _deco
        def get(self, _):
            def _deco(f):
                return f
            return _deco
        def post(self, _):
            def _deco(f):
                return f
            return _deco
    HTTPException = Exception
    app = _DummyApp()
from typing import List, Dict, Any
import asyncio
try:
    from dotenv import load_dotenv
except Exception:
    # dotenv not installed in test environment; use a no-op loader
    def load_dotenv():
        return None
load_dotenv()

# (app is created above — real FastAPI when available, dummy otherwise)

# Database setup
DB_PATH = "transactions.db"

def init_db():
    """Initialize SQLite database with transactions table"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS transactions (
        tx_id TEXT PRIMARY KEY,
        order_id TEXT,
        customer_name TEXT,
        amount REAL,
        currency TEXT,
        status TEXT,
        timestamp TEXT,
        payer TEXT
    )
    """)
    conn.commit()
    conn.close()

def store_transaction(transaction: Dict[str, Any]) -> bool:
    """Store a single transaction in the database"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute("""
        INSERT OR REPLACE INTO transactions 
        (tx_id, order_id, customer_name, amount, currency, status, timestamp, payer)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            transaction.get('tx_id'),
            transaction.get('order_id'),
            transaction.get('customer_name'),
            transaction.get('amount'),
            transaction.get('currency'),
            transaction.get('status'),
            transaction.get('timestamp'),
            transaction.get('payer')
        ))
        conn.commit()
        return True
    except Exception as e:
        print(f"Error storing transaction: {e}")
        return False
    finally:
        conn.close()

def get_transactions_by_status(status: str = None) -> List[Dict[str, Any]]:
    """Retrieve transactions filtered by status"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    if status:
        cursor.execute("SELECT * FROM transactions WHERE status = ?", (status,))
    else:
        cursor.execute("SELECT * FROM transactions")
    
    rows = cursor.fetchall()
    result = [dict(row) for row in rows]
    conn.close()
    return result

def get_non_success_transactions() -> List[Dict[str, Any]]:
    """Retrieve all non-SUCCESS transactions"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM transactions WHERE status != 'SUCCESS'")
    rows = cursor.fetchall()
    result = [dict(row) for row in rows]
    conn.close()
    return result

# FastAPI endpoints
@app.on_event("startup")
async def startup_event():
    """Initialize database on startup"""
    init_db()

@app.get("/transactions/success")
async def get_success_transactions() -> List[Dict[str, Any]]:
    """Get all SUCCESS transactions"""
    return get_transactions_by_status("SUCCESS")

@app.post("/transactions/success")
async def store_and_get_success() -> List[Dict[str, Any]]:
    """Store all SUCCESS transactions from mockdata into the DB and return them.

    This endpoint performs the storage; calling it will persist SUCCESS
    transactions (idempotent because INSERT OR REPLACE is used).
    """
    stored = 0
    for tx in mockdata:
        if str(tx.get("status", "")).upper() == "SUCCESS":
            if store_transaction(tx):
                stored += 1
    # Return the current set of SUCCESS transactions from DB
    return get_transactions_by_status("SUCCESS")


@app.get("/transactions/non_success")
async def get_non_success() -> List[Dict[str, Any]]:
    """Return non-SUCCESS transactions directly from the raw `mockdata`.

    Important: per design, non-SUCCESS transactions are not persisted to the DB
    and are served directly from the source data.
    """
    return [tx for tx in mockdata if str(tx.get("status", "")).upper() != "SUCCESS"]

# Agent setup
gemini_api_key = os.getenv("GEMINI_API_KEY")
external_client = None
model = None
config = None
agent = None

if AsyncOpenAI is not None and OpenAIChatCompletionsModel is not None and RunConfig is not None and Agent is not None:
    external_client = AsyncOpenAI(
        api_key=gemini_api_key,
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
    )

    model = OpenAIChatCompletionsModel(
        model="gemini-2.0-flash",
        openai_client=external_client,
    )

    config = RunConfig(
        model=model,
        model_provider=external_client,
        tracing_disabled=True,
    )

    # Agent instructions for autonomous operation
    agent = Agent(
        name="Financial Expert",
        instructions="""You are a financial transaction processing agent. Your tasks are:

1. Monitor and process transaction data from the mockdata source
2. Store SUCCESS transactions in the SQLite database
3. Provide access to both SUCCESS and non-SUCCESS transactions via API endpoints

Key responsibilities:
- Automatically store SUCCESS transactions in the database
- Ensure data integrity and avoid duplicates using tx_id as the primary key
- Return appropriate status messages for all operations

Available endpoints:
- GET /transactions/success: Returns all SUCCESS transactions
- GET /transactions/non_success: Returns all non-SUCCESS transactions

Database schema:
- transactions table with fields: tx_id, order_id, customer_name, amount, currency, status, timestamp, payer
""",
    )

# Ensure database is initialized before processing
init_db()

# Import mockdata here to avoid circular imports
from mockdata import mockdata

# Process initial SUCCESS transactions
def process_success_transactions():
    """Store all SUCCESS transactions from mockdata"""
    success_count = 0
    for tx in mockdata:
        if tx.get('status') == 'SUCCESS':
            if store_transaction(tx):
                success_count += 1
    return success_count

if __name__ == "__main__":
    # Process initial data
    processed = process_success_transactions()
    print(f"Processed {processed} SUCCESS transactions")
    
    # Run the agent
    try:
        result = Runner.run_sync(
            agent=agent,
            model=model,
            run_config=config,
        )
        print(result.final_output)
    except Exception as e:
        print(f"Error running agent: {e}")