# block_user.py
from datetime import datetime, UTC
from pymongo import MongoClient

client = MongoClient("mongodb://localhost:27017/")
db = client["studentapp"]
blocked = db["blocked_users"]

def block_user(roll_no, reason):
    if blocked.find_one({"roll_no": roll_no}):
        return

    blocked.insert_one({
        "roll_no": roll_no,
        "reason": reason,
        "blocked_at": datetime.now(UTC),
        "status": "blocked"
    })
