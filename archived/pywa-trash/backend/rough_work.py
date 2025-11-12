# --------------------------------------------------------------
# app.py   –   WhatsApp Sales Agent (FastAPI + pywa_async + Gemini)
# --------------------------------------------------------------

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import PlainTextResponse ,JSONResponse  # <-- plain text for Meta
from pywa_async import WhatsApp, filters, utils,types
from pywa_async.types import Message
# from pywa import WhatsApp,filters,utils,types
# from pywa.server.fastapi import Webhook  # ✅ new import
from contextlib import asynccontextmanager
from agent import sales_agent
from agents import Runner, SQLiteSession
import json







# -------------------------- Lifespan ---------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    # ---- startup ------------------------------------------------
    try:
        resp = await wa.send_message(
            to="923012177654",
            text="👋 Welcome to BazaFlow! 🚀 Let’s talk about your products and business goals 💡"
        )
        # resp = await wa.send_message(
        #     to="923012177654",
        #     text="👋 Welcome to BazaFlow! 🚀 Let’s talk about your products and business goals 💡",
        #     buttons=[
        #         types.Button(title="Say Hii !!", callback_data="Gretting"),
        #         types.Button(title="Products", callback_data="help")
        #     ]
        # )
        print("Startup send success:", resp.id)
    except Exception as e:
        print("Startup send error:", e)
    yield
    # ---- shutdown -----------------------------------------------
    print("App shutdown – cleaning up...")

app = FastAPI(lifespan=lifespan)

# -------------------------- WhatsApp client --------------------


wa = WhatsApp(
   
)


# -------------------------- Session store ----------------------
user_sessions: dict[str, SQLiteSession] = {}

# -------------------------- Webhook GET -----------------------
@app.get("/webhook")
async def webhook_get(request: Request):
    print("\n=== WEBHOOK GET HIT 🥶 ===")
    mode = request.query_params.get("hub.mode")
    challenge = request.query_params.get("hub.challenge")
    token = request.query_params.get("hub.verify_token")
    print(f"mode={mode}  token={token}  challenge={challenge}")

    if mode == "subscribe" and token == "test123":
        print("Verification OK – returning plain-text challenge")
        return PlainTextResponse(challenge, media_type="text/plain")

    print("Verification FAILED – 403")
    raise HTTPException(status_code=403, detail="Forbidden token")

# -------------------------- Webhook POST ----------------------


@app.post("/webhook")
async def webhook_post(request: Request):
    body = await request.body()
    print(f"\n=== WEBHOOK POST HIT  😇 ===")

    try:
        data = json.loads(body)
        messages = data.get("entry", [{}])[0].get("changes", [{}])[0].get("value", {}).get("messages", [])
        if not messages:
            print("no messages in webhook payload")
            return {"status": "ok"}

        for msg in messages:
            from_user = msg.get("from")
            text = msg.get("text", {}).get("body", "")
            msg_id = msg["id"]
            print(f"📩 {from_user}: {text}")

            # session handling (same as in your decorator)
            if from_user not in user_sessions:
                session = SQLiteSession(session_id=from_user)
                user_sessions[from_user] = session
                print(f"New SQLiteSession for {from_user}")
            session = user_sessions[from_user]

            # run agent directly (bypass wa.process_update)
            try:
                response = await Runner.run(input=text, starting_agent=sales_agent, session=session)
                reply_text = response.final_output
            except Exception as e:
                print("Agent run error:", e)
                reply_text = "Sorry, SalesAgent's busy – try again!"

            # send reply via wa API
            try:
                # msg= Message
                resp = await wa.send_message(to=from_user, text=reply_text)
                # React to the original message
                # await msg.react("✅")
                await wa.send_reaction(
                        to=from_user,
                        emoji='✅',
                        message_id=msg_id
                )   
                # print(f"Reacted to {msg_id}")
                print(f"[Webhook Reply Sent] ID: {getattr(resp, 'id', '<no-id>')}")
            except Exception as e:
                print("wa.send_message error:", e)

        return {"status": "ok"}
    except Exception as e:
        print("ERROR:", e)
        return JSONResponse({"error": str(e)}, status_code=500)
# ...existing code...



# @app.post("/webhook")
# async def webhook_post(request: Request):
#     body = await request.body()
#     print(f"\n=== WEBHOOK POST HIT  😇 ===")
    

#     try:
#         data = json.loads(body)
#         for msg in data.get("entry", [{}])[0].get("changes", [{}])[0].get("value", {}).get("messages", []):
#             from_user = msg["from"]
#             text = msg["text"]["body"]
#             print(f"📩 {from_user}: {text}")

#             # THIS SENDS TO WHATSAPP
#             # await wa.send_message(to=from_user, text=f"Echo: {text}")

#             await wa.process_update(body)
            

#         return {"status": "ok"}
#     except Exception as e:
#         print("ERROR:", e)
#         return {"error": "bad"}, 500
    



# -------------------------- Message handler -------------------
@wa.on_message(filters.text)
async def handle_incoming_message(client: WhatsApp, msg: Message):
    user_id = msg.from_user.wa_id
    print(f"\n[Incoming] From: {user_id} | Text: {msg.text}")

    try:
        # ---- session ------------------------------------------------
        if user_id not in user_sessions:
            session = SQLiteSession(session_id=user_id)
            user_sessions[user_id] = session
            print(f"New SQLiteSession for {user_id}")
        session = user_sessions[user_id]

        # ---- agent --------------------------------------------------
        response = await Runner.run(input=msg.text, starting_agent=sales_agent,session=session)
        reply_text = response.final_output

        # ---- reply --------------------------------------------------
        reply = await msg.reply_text(reply_text)
        print(f"[SalesAgent Reply Sent] ID: {reply.id}")
        await msg.react("Checkmark")

    except Exception as e:
        await msg.reply_text("Sorry, SalesAgent's busy – try again!")
        print(f"[SalesAgent Error] {e}")


# @wa.on_message(filters.text)
# async def handle_incoming_message(client: WhatsApp, msg: Message):
#     print(f"[Incoming] From: {msg.from_user.wa_id} | Text: {msg.text}")
#     response_text = f"Received: '{msg.text}'! AI agent online – what's your query?"
#     reply = await msg.reply_text(response_text)
#     print(f"[Reply Sent] ID: {reply.id}")
#     await msg.react("✅")

# -------------------------- (optional) manual send ------------
# @app.post("/send_message")
# async def send_msg(phone: str = Form(...), text: str = Form(...)):
#     resp = await wa.send_message(to=phone, text=text)
#     return {"status": "sent", "msg_id": resp.id}




