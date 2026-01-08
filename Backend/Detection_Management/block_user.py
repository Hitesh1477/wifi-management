# block_user.py
from datetime import datetime, timedelta, UTC
from pymongo import MongoClient

client = MongoClient("mongodb://localhost:27017/")
db = client["studentapp"]
blocked_users = db["blocked_users"]

def block_user(roll_no, confidence, reason):
    """
    Auto-ban logic:
    - confidence >= 0.95 => permanent ban
    - confidence >= 0.75 => 24-hour temporary ban
    """
    existing = blocked_users.find_one({"roll_no": roll_no, "status": "blocked"})
    if existing and existing.get("ban_type") == "permanent":
        return

    now = datetime.now(UTC)

    if confidence >= 0.95:
        ban_type = "permanent"
        expires_at = None
    elif confidence >= 0.75:
        ban_type = "temporary"
        expires_at = now + timedelta(hours=24)
    else:
        return

    blocked_users.update_one(
        {"roll_no": roll_no},
        {
            "$set": {
                "roll_no": roll_no,
                "ban_type": ban_type,
                "confidence": round(confidence, 3),
                "reason": reason,
                "blocked_at": now,
                "expires_at": expires_at,
                "status": "blocked"
            }
        },
        upsert=True
    )
