import os
import json
import firebase_admin
from firebase_admin import credentials, firestore
from dotenv import load_dotenv

load_dotenv()

# Check for credentials
cred = None
use_firebase = False

# 1. Look for local service-account.json file
cred_path = os.path.join(os.path.dirname(__file__), "service-account.json")
if os.path.exists(cred_path):
    try:
        cred = credentials.Certificate(cred_path)
    except Exception as e:
        print(f"ERROR: Failed to load local service-account.json: {e}")

# 2. Look for Environment Variable containing JSON string (safer for public repositories)
if not cred:
    service_account_json = os.environ.get("FIREBASE_SERVICE_ACCOUNT_JSON")
    if service_account_json:
        try:
            service_account_info = json.loads(service_account_json)
            cred = credentials.Certificate(service_account_info)
        except Exception as e:
            print(f"ERROR: Failed to parse FIREBASE_SERVICE_ACCOUNT_JSON env var: {e}")

# Initialize Firebase with whatever certificate we successfully obtained
if cred:
    try:
        try:
            firebase_app = firebase_admin.initialize_app(cred)
        except ValueError:
            firebase_app = firebase_admin.get_app()
        db = firestore.client()
        use_firebase = True
        print("Firebase Admin SDK initialized successfully with credentials.")
    except Exception as e:
        print(f"ERROR: Failed to initialize Firebase: {e}. Falling back to in-memory DB.")
        use_firebase = False
        _memory_db = []
else:
    print("WARNING: No Firebase credentials found. Using in-memory fallback database.")
    use_firebase = False
    _memory_db = []

def save_message(role: str, content: str):
    """
    Saves a chat message (role: 'user' or 'model') to the 'chat_history' collection.
    """
    if use_firebase:
        try:
            db.collection("chat_history").add({
                "role": role,
                "content": content,
                "created_at": firestore.SERVER_TIMESTAMP
            })
        except Exception as e:
            print(f"Error saving message to Firestore: {e}")
    else:
        import datetime
        _memory_db.append({
            "role": role,
            "content": content,
            "created_at": datetime.datetime.now().isoformat()
        })

def get_chat_history(limit: int = 20):
    """
    Retrieves the most recent chat history, in chronological order.
    """
    if use_firebase:
        try:
            docs = db.collection("chat_history").order_by("created_at", direction=firestore.Query.DESCENDING).limit(limit).stream()
            history = []
            for doc in docs:
                data = doc.to_dict()
                created_at = data.get("created_at")
                if created_at and hasattr(created_at, "isoformat"):
                    created_at = created_at.isoformat()
                history.append({
                    "role": data.get("role", "user"),
                    "content": data.get("content", ""),
                    "created_at": created_at
                })
            # Reverse to maintain ascending chronological order
            return history[::-1]
        except Exception as e:
            print(f"Error reading history from Firestore: {e}")
            return []
    else:
        return _memory_db[-limit:]