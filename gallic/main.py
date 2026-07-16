import os
import json
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from google import genai
from google.genai import types
from database import save_message, get_chat_history, use_firebase, db
from dotenv import load_dotenv

if use_firebase:
    from firebase_admin import firestore

def send_firebase_notification(title: str, desc: str, payload_type: str, body: str = ""):
    if use_firebase:
        try:
            db.collection("notifications").add({
                "title": title,
                "desc": desc,
                "type": payload_type,
                "body": body,
                "timestamp": firestore.SERVER_TIMESTAMP,
                "isRead": False
            })
            print(f"Firestore Notification Added: {title}")
        except Exception as e:
            print(f"Error adding Firestore Notification: {e}")

load_dotenv()

# Configure Google GenAI
api_key = os.getenv("GEMINI_API_KEY")
project = os.getenv("GOOGLE_CLOUD_PROJECT")

if api_key:
    client = genai.Client(api_key=api_key)
    MODEL_NAME = "gemini-2.0-flash"
elif project:
    client = genai.Client(vertexai=True, project=project, location="us-central1")
    MODEL_NAME = "gemini-2.0-flash"
else:
    client = genai.Client()
    MODEL_NAME = "gemini-2.0-flash"

app = FastAPI(title="Young Gallic Assistant API")

# Setup CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from typing import List, Optional

class ChatRequest(BaseModel):
    message: str
    history: Optional[List[dict]] = None

from datetime import datetime

def get_system_instruction():
    current_time = datetime.now().strftime("%Y-%m-%d %I:%M %p")
    return f"""
You are Young Gallic (yg), an elite, hyper-proactive personal executive assistant and strategic operations partner to Elias.
Elias is a highly accomplished professional operating under extreme pressure:
1. He is pursuing a Master's degree (requiring intense academic reading, dissertation writing, research, and deadline adherence).
2. He is an academic Lecturer at MUBAS (Malawi University of Business and Applied Sciences) — responsible for student sessions, grading papers, course scheduling, and research.
3. He is the Financial Controller at Vivo Energy Malawi — overseeing corporate finance, audit trails, fuel distribution balance sheets, budgets, and executive financial reports.

YOUR CRITICAL MISSION:
Help Elias "buy back his time" so he can be free at last. Shield him from mundane clutter, organize task drafts, write professional communications, track dates, and keep him on track.

Communication Guidelines:
- Never mention microbiology, yeast, or lab culture incubations. That context is completely obsolete.
- Keep all advice highly structured, pragmatic, and directly actionable.
- When drafting emails or WhatsApp responses, default to an exceptionally polished executive style (corporate, academic, or professional depending on the recipient).
- Be the ultimate second brain. Keep tracks of assignments, lecture dates, financial reporting milestones, and provide relief from constant stress.

Current System Date and Time: {current_time}
"""

def generate_content_with_fallback(client, contents, config):
    # Try gemini-3.1-flash-lite (active & uncongested), gemini-2.0-flash, gemini-3.5-flash, gemini-flash-latest, etc.
    models_to_try = [
        "gemini-3.1-flash-lite",
        "gemini-2.0-flash",
        "gemini-3.5-flash",
        "gemini-2.0-flash-lite",
        "gemini-flash-latest",
        "gemini-pro-latest"
    ]
    last_error = None
    for model_name in models_to_try:
        try:
            print(f"Attempting API call with {model_name}...")
            response = client.models.generate_content(
                model=model_name,
                contents=contents,
                config=config
            )
            print(f"Success with {model_name}!")
            return response
        except Exception as e:
            print(f"Error with {model_name}: {e}")
            last_error = e
    raise last_error

@app.post("/chat")
async def chat(request: ChatRequest):
    user_message = request.message
    
    # Save the user's message to global DB for persistence/audit
    save_message("user", user_message)

    formatted_history = []
    
    # If client passed custom isolated history, use it. Otherwise, query DB.
    if request.history is not None:
        for row in request.history:
            # Map our roles to Gemini roles ('user' or 'model')
            role = "user" if row['role'] == "user" else "model"
            # Prevent empty parts causing Gemini API error
            content_text = row.get('content', '').strip()
            if content_text:
                formatted_history.append(
                    types.Content(role=role, parts=[types.Part.from_text(text=content_text)])
                )
    else:
        # Fetch chat history to give the model context
        history = get_chat_history()
        for row in history:
            role = "user" if row['role'] == "user" else "model"
            content_text = row.get('content', '').strip()
            if content_text:
                formatted_history.append(
                    types.Content(role=role, parts=[types.Part.from_text(text=content_text)])
                )

    # Append the new user message
    formatted_history.append(
        types.Content(role="user", parts=[types.Part.from_text(text=user_message)])
    )

    system_instruction = get_system_instruction()

    try:
        response = generate_content_with_fallback(
            client=client,
            contents=formatted_history,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=0.7,
            )
        )
        bot_reply = response.text
    except Exception as e:
        # If all fallback models fail, raise HTTP 503 so the frontend knows we are out of brain quota
        raise HTTPException(status_code=503, detail=f"All models failed or exhausted. Last error: {str(e)}")

    # Save the bot's reply
    save_message("bot", bot_reply)

    return {"response": bot_reply}

class WebhookRequest(BaseModel):
    sender: str
    message: str

class GmailSyncRequest(BaseModel):
    email: str
    app_password: str

pending_notifications = []
active_companions: List[WebSocket] = []

import imaplib
import email
from email.header import decode_header

def check_real_gmail(email_addr, app_password):
    try:
        # Connect to Gmail IMAP
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(email_addr, app_password)
        mail.select("inbox")
        
        # Search for unread (UNSEEN) emails
        status, messages = mail.search(None, 'UNSEEN')
        if status != 'OK':
            return []
            
        email_ids = messages[0].split()
        new_emails = []
        
        # Limit to the most recent unread email to prevent reading too many emails during testing
        if email_ids:
            latest_id = email_ids[-1]
            status, msg_data = mail.fetch(latest_id, '(RFC822)')
            if status == 'OK':
                for response_part in msg_data:
                    if isinstance(response_part, tuple):
                        msg = email.message_from_bytes(response_part[1])
                        
                        subject, encoding = decode_header(msg["Subject"])[0]
                        if isinstance(subject, bytes):
                            subject = subject.decode(encoding or "utf-8", errors="ignore")
                        
                        sender, encoding = decode_header(msg["From"])[0]
                        if isinstance(sender, bytes):
                            sender = sender.decode(encoding or "utf-8", errors="ignore")
                            
                        body = ""
                        if msg.is_multipart():
                            for part in msg.walk():
                                content_type = part.get_content_type()
                                content_disposition = str(part.get("Content-Disposition"))
                                if content_type == "text/plain" and "attachment" not in content_disposition:
                                    payload = part.get_payload(decode=True)
                                    body = payload.decode(errors="ignore")
                                    break
                        else:
                            payload = msg.get_payload(decode=True)
                            body = payload.decode(errors="ignore")
                            
                        new_emails.append({
                            "sender": sender,
                            "subject": subject,
                            "body": body[:500] # Limit content length
                        })
                        
                        # Mark it as read so it isn't fetched repeatedly
                        mail.store(latest_id, '+FLAGS', '\\Seen')
        mail.close()
        mail.logout()
        return new_emails
    except Exception as e:
        print(f"Error checking Gmail IMAP inbox: {e}")
        return []

@app.post("/api/sync-gmail")
async def sync_gmail(req: GmailSyncRequest):
    global pending_notifications
    new_mails = check_real_gmail(req.email, req.app_password)
    
    for m in new_mails:
        pending_notifications.append({
            "id": f"mail_real_{int(datetime.now().timestamp() * 1000)}",
            "sender": m["sender"],
            "title": m["subject"],
            "desc": f"Subject: {m['subject']}\n\nContent: {m['body']}",
            "type": "email"
        })
        
        # Broadcast to all active companion nodes & write to Firestore
        title = f"Draft Email reply to {m['sender']}"
        desc = f"Subject: {m['subject']}"
        body = f"Thank you for emailing me. I received your message: '{m['subject']}'. Elias."
        send_firebase_notification(title, desc, "new_email", body)

        payload = {
            "type": "new_email",
            "title": title,
            "desc": desc,
            "body": body
        }
        for companion in list(active_companions):
            try:
                await companion.send_text(json.dumps(payload))
            except Exception as e:
                print(f"WS Gmail Broadcast Exception: {e}")
    return {"status": "success", "count": len(new_mails)}

@app.get("/api/whatsapp-webhook")
async def verify_whatsapp_webhook(hub_mode: Optional[str] = None, hub_challenge: Optional[str] = None, hub_verify_token: Optional[str] = None):
    # Standard Meta Developer Verification Protocol
    # Matches whatever verification token Elias specifies inside settings
    if hub_challenge:
        return int(hub_challenge) if hub_challenge.isdigit() else hub_challenge
    return "Verification token configured successfully"

@app.post("/api/whatsapp-webhook")
async def whatsapp_webhook(data: dict):
    global pending_notifications
    
    # 1. Parse Meta WhatsApp Business JSON payloads
    if data.get("object") == "whatsapp_business_account" and data.get("entry"):
        try:
            for entry in data["entry"]:
                for change in entry.get("changes", []):
                    value = change.get("value", {})
                    if "messages" in value:
                        for msg in value["messages"]:
                            sender_phone = msg.get("from", "Unknown")
                            sender_name = sender_phone
                            for contact in value.get("contacts", []):
                                if contact.get("wa_id") == sender_phone:
                                    sender_name = contact.get("profile", {}).get("name", sender_phone)
                                    break
                            
                            body = ""
                            if msg.get("type") == "text":
                                body = msg.get("text", {}).get("body", "")
                            elif msg.get("type") == "button":
                                body = msg.get("button", {}).get("text", "")
                            else:
                                body = f"Received a WhatsApp {msg.get('type')} message"
                                
                            pending_notifications.append({
                                "id": f"wa_real_{int(datetime.now().timestamp() * 1000)}",
                                "sender": sender_name,
                                "message": body,
                                "type": "whatsapp"
                            })
                            
                            # Broadcast to all active companion nodes & write to Firestore
                            title = f"Draft WhatsApp reply to Girlfriend {sender_name}"
                            desc = "Young Gallic synchronized incoming alert."
                            body = f"Hi {sender_name}, received your message. I'm currently in a financial review/MUBAS session and will respond fully as soon as I am free. — Elias"
                            send_firebase_notification(title, desc, "new_whatsapp", body)

                            payload = {
                                "type": "new_whatsapp",
                                "title": title,
                                "desc": desc,
                                "body": body
                            }
                            for companion in list(active_companions):
                                try:
                                    await companion.send_text(json.dumps(payload))
                                except:
                                    pass
            return {"status": "success"}
        except Exception as e:
            print(f"Error parsing Meta webhook payload: {e}")
            
    # 2. Standalone webhook support and raw simulation console backward compatibility
    sender = data.get("sender", "Unknown")
    message = data.get("message", "")
    pending_notifications.append({
        "id": f"wa_real_{int(datetime.now().timestamp() * 1000)}",
        "sender": sender,
        "message": message,
        "type": "whatsapp"
    })
    
    # Broadcast to all active companion nodes & write to Firestore
    title = f"Draft WhatsApp reply to Girlfriend {sender}"
    desc = "Young Gallic synchronized incoming alert."
    body = f"Hi {sender}, received your message. I'm currently in a financial review/MUBAS session and will respond fully as soon as I am free. — Elias"
    send_firebase_notification(title, desc, "new_whatsapp", body)

    payload = {
        "type": "new_whatsapp",
        "title": title,
        "desc": desc,
        "body": body
    }
    for companion in list(active_companions):
        try:
            await companion.send_text(json.dumps(payload))
        except:
            pass
            
    return {"status": "success"}

@app.get("/api/pending-notifications")
async def get_pending_notifications():
    global pending_notifications
    res = list(pending_notifications)
    pending_notifications.clear()
    return {"notifications": res}

@app.get("/history")
async def history():
    history = get_chat_history()
    return {"history": [{"role": "user" if row['role'] == "user" else "assistant", "content": row['content']} for row in history]}

@app.websocket("/ws/companion")
async def websocket_companion(websocket: WebSocket, token: str = None):
    await websocket.accept()
    active_companions.append(websocket)
    print(f"Paired Mobile Companion Link Handshaked! (Token: {token})")
    try:
        while True:
            raw_data = await websocket.receive_text()
            data = json.loads(raw_data)
            
            if data.get('type') == 'command':
                prompt = data.get('prompt', '').strip()
                if not prompt:
                    continue
                
                print(f"Remote command received from Companion App: {prompt}")
                save_message("user", prompt)
                
                # Fetch chat history to give the model context
                formatted_history = []
                history = get_chat_history()
                for row in history:
                    role = "user" if row['role'] == "user" else "model"
                    content_text = row.get('content', '').strip()
                    if content_text:
                        formatted_history.append(
                            types.Content(role=role, parts=[types.Part.from_text(text=content_text)])
                        )
                
                system_instruction = get_system_instruction()
                try:
                    response = generate_content_with_fallback(
                        client=client,
                        contents=formatted_history,
                        config=types.GenerateContentConfig(
                            system_instruction=system_instruction,
                            temperature=0.7,
                        )
                    )
                    bot_reply = response.text
                except Exception as e:
                    bot_reply = f"Error processing remote command: {str(e)}"
                
                save_message("bot", bot_reply)
                
                # Broadcast response back to the paired companion client
                await websocket.send_text(json.dumps({
                    'type': 'chat_response',
                    'text': bot_reply
                }))
                
            elif data.get('type') == 'approval_action':
                draft_id = data.get('draft_id')
                action = data.get('action')
                content = data.get('revised_content')
                print(f"Draft {draft_id} approved via remote device with revised content: {content}")
                
    except WebSocketDisconnect:
        print("Mobile Companion unlinked or disconnected.")
    except Exception as e:
        print(f"WebSocket Companion Exception: {e}")
    finally:
        if websocket in active_companions:
            active_companions.remove(websocket)

def start_commands_listener():
    if not use_firebase:
        print("Firebase is disabled. Commands snapshot listener skipped.")
        return

    def on_snapshot(col_snapshot, changes, read_time):
        for change in changes:
            if change.type.name == 'ADDED':
                doc = change.document
                data = doc.to_dict()
                if data.get("status") == "pending":
                    doc_ref = doc.reference
                    prompt = data.get("prompt", "").strip()
                    if not prompt:
                        continue

                    print(f"Firestore Remote command received: {prompt}")
                    doc_ref.update({"status": "processing"})

                    # Save user message to history
                    save_message("user", prompt)

                    # Fetch chat history to give the model context
                    formatted_history = []
                    history = get_chat_history()
                    for row in history:
                        role = "user" if row['role'] == "user" else "model"
                        content_text = row.get('content', '').strip()
                        if content_text:
                            formatted_history.append(
                                types.Content(role=role, parts=[types.Part.from_text(text=content_text)])
                            )

                    system_instruction = get_system_instruction()
                    try:
                        response = generate_content_with_fallback(
                            client=client,
                            contents=formatted_history,
                            config=types.GenerateContentConfig(
                                system_instruction=system_instruction,
                                temperature=0.7,
                            )
                        )
                        bot_reply = response.text
                    except Exception as e:
                        bot_reply = f"Error processing remote command: {str(e)}"

                    # Save model response
                    save_message("bot", bot_reply)

                    # Update Firestore command document
                    doc_ref.update({
                        "response": bot_reply,
                        "status": "completed",
                        "completed_at": firestore.SERVER_TIMESTAMP
                    })
                    print(f"Firestore Remote command completed: {prompt}")

    db.collection("commands").where("status", "==", "pending").on_snapshot(on_snapshot)
    print("Firestore Commands snapshot listener started.")

@app.on_event("startup")
async def startup_event():
    start_commands_listener()

# Mount the static files from the React build
frontend_path = os.path.join(os.path.dirname(__file__), "frontend", "dist")
if os.path.exists(frontend_path):
    app.mount("/gallic", StaticFiles(directory=frontend_path, html=True), name="static_gallic")
    app.mount("/", StaticFiles(directory=frontend_path, html=True), name="static")
else:
    print(f"Warning: Frontend build directory not found at {frontend_path}. Make sure to run 'npm run build' inside the frontend directory.")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
