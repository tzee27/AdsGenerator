import firebase_admin
from firebase_admin import credentials, firestore
import os
from app.core.config import settings

# Get the absolute path to the credentials file
cred_path = os.getenv("FIREBASE_CREDENTIALS_PATH", "firebase-credentials.json")
if not os.path.isabs(cred_path):
    # Assume it's in the backend root directory
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    cred_path = os.path.join(base_dir, cred_path)

# Initialize Firebase Admin SDK
if not firebase_admin._apps:
    try:
        cred = credentials.Certificate(cred_path)
        firebase_admin.initialize_app(cred)
    except Exception as e:
        print(f"Warning: Failed to initialize Firebase Admin SDK: {e}")

# Get Firestore db client
def get_db():
    return firestore.client()
