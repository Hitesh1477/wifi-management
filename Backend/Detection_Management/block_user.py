# block_user.py
from datetime import datetime, timedelta, UTC
from pymongo import MongoClient

client = MongoClient("mongodb://localhost:27017/")
db = client["studentapp"]
blocked_users = db["blocked_users"]
anomalies = db["anomalies"]

def block_user(roll_no, confidence, reason):
    """
    Auto-ban logic:
    - confidence >= 0.95 => permanent ban
    - confidence >= 0.75 => 24-hour temporary ban
    """
    existing = blocked_users.find_one({"roll_no": roll_no, "status": "blocked"})
    if existing and existing.get("ban_type") == "permanent":
        print(f"ℹ️  {roll_no} already permanently banned")
        return False

    now = datetime.now(UTC)

    if confidence >= 0.95:
        ban_type = "permanent"
        expires_at = None
    elif confidence >= 0.75:
        ban_type = "temporary"
        expires_at = now + timedelta(hours=24)
    else:
        print(f"ℹ️  {roll_no} confidence too low ({confidence:.1%}) - not blocking")
        return False

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
    
    print(f"🚫 Blocked {roll_no} ({ban_type}) - {reason}")
    return True


def auto_block_from_anomalies():
    """
    Check recent anomalies and block users with high confidence
    """
    print("=" * 50)
    print("🔍 Checking recent anomalies for auto-blocking...")
    print("=" * 50)
    
    # Get recent anomalies (last 24 hours)
    since = datetime.now(UTC) - timedelta(hours=24)
    recent_anomalies = anomalies.find({
        "timestamp": {"$gte": since},
        "confidence": {"$gte": 0.75}
    }).sort("timestamp", -1)
    
    blocked_count = 0
    checked_users = set()
    
    for anom in recent_anomalies:
        roll_no = anom.get("roll_no")
        if not roll_no or roll_no in checked_users:
            continue
        
        checked_users.add(roll_no)
        confidence = anom.get("confidence", 0)
        reason = anom.get("reason", "Anomalous behavior detected")
        
        print(f"\n📊 {roll_no}: {confidence:.1%} confidence")
        
        if block_user(roll_no, confidence, reason):
            blocked_count += 1
    
    print(f"\n✅ Checked {len(checked_users)} user(s), blocked {blocked_count}")


if __name__ == "__main__":
    auto_block_from_anomalies()
