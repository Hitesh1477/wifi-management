# session_lookup.py
from pymongo import MongoClient
from datetime import datetime, UTC

client = MongoClient("mongodb://localhost:27017/", serverSelectionTimeoutMS=5000)
db = client["studentapp"]
sessions_collection = db["active_sessions"]
blocked_users = db["blocked_users"]

def is_user_blocked(roll_no):
    ban = blocked_users.find_one({"roll_no": roll_no, "status": "blocked"})
    if not ban:
        return False

    if ban.get("ban_type") == "permanent":
        return True

    expires_at = ban.get("expires_at")
    if expires_at and datetime.now(UTC) >= expires_at:
        blocked_users.update_one(
            {"roll_no": roll_no},
            {"$set": {"status": "expired"}}
        )
        return False

    return True

def get_roll_no_from_ip(client_ip):
    session = sessions_collection.find_one({
        "client_ip": client_ip,
        "status": "active"
    })

    if not session or "roll_no" not in session:
        return None

    roll_no = session["roll_no"]

    if is_user_blocked(roll_no):
        return None

    return roll_no

def get_all_active_ips():
    sessions = sessions_collection.find({"status": "active"})
    active_ips = set()

    for s in sessions:
        roll_no = s.get("roll_no")
        if "client_ip" in s and not is_user_blocked(roll_no):
            active_ips.add(s["client_ip"])

    return active_ips

def is_user_active(roll_no):
    return sessions_collection.find_one({
        "roll_no": roll_no,
        "status": "active"
    }) is not None
