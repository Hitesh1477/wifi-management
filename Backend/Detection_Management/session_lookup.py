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
    Returns roll_no if found, otherwise returns None (user not logged in).
    """
    if sessions_collection is None:
        return None
    
    try:
        session = sessions_collection.find_one({"client_ip": client_ip, "status": "active"})
        if session and "roll_no" in session:
            return session["roll_no"]
        else:
            # No active session found for this IP - user not logged in
            return None
    except Exception as e:
        print(f"⚠️ Error looking up session for IP {client_ip}: {e}")
        return None

def is_user_active(roll_no):
    """
    Check if a user with the given roll_no has an active session.
    Returns True if user is logged in, False otherwise.
    """
    if sessions_collection is None:
        return False
    
    try:
        session = sessions_collection.find_one({"roll_no": roll_no, "status": "active"})
        return session is not None
    except Exception as e:
        print(f"⚠️ Error checking session for roll_no {roll_no}: {e}")
        return False

def get_all_active_ips():
    """
    Get all IPs that have active sessions (logged in users).
    Returns a set of IP addresses.
    """
    if sessions_collection is None:
        return set()
    
    try:
        sessions = sessions_collection.find({"status": "active"})
        return {s["client_ip"] for s in sessions if "client_ip" in s}
    except Exception as e:
        print(f"⚠️ Error getting active IPs: {e}")
        return set()

