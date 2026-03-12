# block_user.py
from datetime import datetime, timedelta, UTC
import os
import sys
from pymongo import MongoClient

client = MongoClient("mongodb://localhost:27017/")
db = client["studentapp"]
blocked_users = db["blocked_users"]
anomalies = db["anomalies"]
sessions_collection = db["active_sessions"]
users_collection = db["users"]


def _ensure_backend_root_on_path():
    backend_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if backend_root not in sys.path:
        sys.path.insert(0, backend_root)


def _safe_non_negative_int(value):
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        return 0


def _sync_usage_before_block(roll_no, active_session, now):
    client_ip = (active_session or {}).get("client_ip")
    if not client_ip:
        return

    try:
        _ensure_backend_root_on_path()
        from linux_firewall_manager import get_usage_for_client_ip

        usage = get_usage_for_client_ip(client_ip) or {}
    except Exception as error:
        print(f"⚠️ Failed reading usage counters for {roll_no} ({client_ip}): {error}")
        return

    current_upload = _safe_non_negative_int(usage.get("upload_bytes"))
    current_download = _safe_non_negative_int(usage.get("download_bytes"))

    accounted_upload = _safe_non_negative_int(active_session.get("usage_accounted_upload_bytes"))
    accounted_download = _safe_non_negative_int(active_session.get("usage_accounted_download_bytes"))

    delta_upload = current_upload - accounted_upload if current_upload >= accounted_upload else current_upload
    delta_download = current_download - accounted_download if current_download >= accounted_download else current_download
    delta_total = max(0, delta_upload + delta_download)

    if delta_total > 0:
        users_collection.update_one(
            {"roll_no": roll_no},
            {
                "$inc": {
                    "total_data_bytes": delta_total,
                    "total_upload_bytes": max(0, delta_upload),
                    "total_download_bytes": max(0, delta_download),
                },
                "$set": {"data_usage_updated_at": now},
            },
        )

    sessions_collection.update_one(
        {"_id": active_session["_id"]},
        {
            "$set": {
                "usage_upload_bytes": current_upload,
                "usage_download_bytes": current_download,
                "usage_total_bytes": current_upload + current_download,
                "usage_accounted_upload_bytes": current_upload,
                "usage_accounted_download_bytes": current_download,
                "usage_last_sync": now,
            }
        },
    )


def _force_logout_if_active(roll_no, reason):
    active_session = sessions_collection.find_one({"roll_no": roll_no, "status": "active"})
    if not active_session:
        return False

    client_ip = active_session.get("client_ip")
    now = datetime.now(UTC)

    _sync_usage_before_block(roll_no, active_session, now)

    if client_ip:
        try:
            _ensure_backend_root_on_path()
            from linux_firewall_manager import block_authenticated_user

            block_authenticated_user(client_ip)
        except Exception as e:
            print(f"⚠️ Failed to revoke firewall access for {roll_no} ({client_ip}): {e}")

    sessions_collection.update_many(
        {"roll_no": roll_no, "status": "active"},
        {
            "$set": {
                "status": "terminated",
                "logout_reason": "security_block",
                "logout_message": reason,
                "logout_at": now,
            }
        },
    )

    try:
        _ensure_backend_root_on_path()
        from bandwidth_manager import apply_bandwidth_for_active_users

        apply_bandwidth_for_active_users()
    except Exception as e:
        print(f"⚠️ Failed to refresh bandwidth policies after blocking {roll_no}: {e}")

    print(f"🔒 Force-logged out {roll_no} due to malicious activity")
    return True

def block_user(roll_no, confidence, reason):
    """
    Auto-ban logic:
    - confidence >= 0.95 => permanent ban
    - confidence >= 0.75 => 24-hour temporary ban
    """
    existing = blocked_users.find_one({"roll_no": roll_no, "status": "blocked"})
    if existing and existing.get("ban_type") == "permanent":
        print(f"ℹ️  {roll_no} already permanently banned")
        _force_logout_if_active(roll_no, reason)
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
    _force_logout_if_active(roll_no, reason)
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
