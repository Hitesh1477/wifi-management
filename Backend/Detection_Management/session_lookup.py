# session_lookup.py
from pymongo import MongoClient

try:
    client = MongoClient("mongodb://localhost:27017/", serverSelectionTimeoutMS=5000)
    db = client["studentapp"]
    sessions_collection = db["active_sessions"]
    print("✅ Session lookup connected to MongoDB")
except Exception as e:
    print(f"⚠️ Session lookup MongoDB connection warning: {e}")
    sessions_collection = None

def get_roll_no_from_ip(client_ip):
    """
    Lookup roll number from client IP address using active sessions.
    Returns roll_no if found, otherwise returns the IP address.
    """
    if sessions_collection is None:
        return client_ip
    
    try:
        session = sessions_collection.find_one({"client_ip": client_ip, "status": "active"})
        if session and "roll_no" in session:
            return session["roll_no"]
        else:
            # No active session found for this IP
            return client_ip
    except Exception as e:
        print(f"⚠️ Error looking up session for IP {client_ip}: {e}")
        return client_ip
