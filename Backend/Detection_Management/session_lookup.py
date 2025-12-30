# session_lookup.py
from pymongo import MongoClient

try:
    client = MongoClient("mongodb://localhost:27017/", serverSelectionTimeoutMS=5000)
    db = client["studentapp"]
    sessions_collection = db["active_sessions"]
    blocked_users = db["blocked_users"]
    print("✅ Session lookup connected to MongoDB")
except Exception as e:
    print(f"⚠️ MongoDB connection warning: {e}")
    sessions_collection = None
    blocked_users = None


def is_user_blocked(roll_no):
    if blocked_users is None:
        return False
    return blocked_users.find_one({"roll_no": roll_no, "status": "blocked"}) is not None


def get_roll_no_from_ip(client_ip):
    """
    Lookup roll number from client IP.
    Blocked users are ignored.
    """
    if sessions_collection is None:
        return None

    try:
        session = sessions_collection.find_one({
            "client_ip": client_ip,
            "status": "active"
        })

        if not session or "roll_no" not in session:
            return None

        roll_no = session["roll_no"]

        # 🔒 Block check
        if is_user_blocked(roll_no):
            print(f"🚫 Blocked user detected: {roll_no}")
            return None

        return roll_no

    except Exception as e:
        print(f"⚠️ Error looking up session for IP {client_ip}: {e}")
        return None


def is_user_active(roll_no):
    if sessions_collection is None:
        return False

    try:
        return sessions_collection.find_one({
            "roll_no": roll_no,
            "status": "active"
        }) is not None
    except Exception:
        return False


def get_all_active_ips():
    if sessions_collection is None:
        return set()

    try:
        sessions = sessions_collection.find({"status": "active"})
        return {
            s["client_ip"]
            for s in sessions
            if "client_ip" in s and not is_user_blocked(s.get("roll_no"))
        }
    except Exception:
        return set()
