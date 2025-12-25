from datetime import datetime, timedelta, UTC
from pymongo import MongoClient

# =========================
# MongoDB Setup
# =========================
client = MongoClient("mongodb://localhost:27017/")
db = client["studentapp"]

detections = db["detections"]
anomalies = db["anomalies"]

# =========================
# Configuration
# =========================
WINDOW_MINUTES = 5

APP_USAGE_THRESHOLD = 5
CATEGORY_ABUSE_RATIO = 0.3
SPIKE_MULTIPLIER = 2.5

AUTO_BAN_LIMIT = 3
AUTO_BAN_WINDOW_MINUTES = 30

# Fixed window identifier (prevents duplicates)
WINDOW_START = datetime.now(UTC).replace(second=0, microsecond=0)

# =========================
# Aggregate Recent Activity
# =========================
def aggregate_recent_activity():
    since = datetime.now(UTC) - timedelta(minutes=WINDOW_MINUTES)

    pipeline = [
        {
            "$match": {
                "timestamp": {"$gte": since},
                "domain": {"$exists": True},
                "roll_no": {"$exists": True},
                "client_ip": {"$ne": ""},
                "category": {"$ne": "general"}   # 🚫 ignore system/background traffic
            }
        },
        {
            "$group": {
                "_id": {
                    "roll_no": "$roll_no",
                    "app_name": "$app_name",
                    "category": "$category",
                    "client_ip": "$client_ip"
                },
                "count": {"$sum": 1}
            }
        }
    ]

    data = {}

    for r in detections.aggregate(pipeline):
        roll_no = r["_id"]["roll_no"]
        app = r["_id"]["app_name"]
        category = r["_id"]["category"]
        ip = r["_id"]["client_ip"]
        count = r["count"]

        if roll_no not in data:
            data[roll_no] = {
                "client_ip": ip,
                "total": 0,
                "apps": {},
                "categories": {}
            }

        data[roll_no]["total"] += count
        data[roll_no]["apps"][app] = data[roll_no]["apps"].get(app, 0) + count
        data[roll_no]["categories"][category] = (
            data[roll_no]["categories"].get(category, 0) + count
        )

    return data

# =========================
# Rule 1: Excessive App Usage
# =========================
def rule_excessive_app_usage(activity):
    for roll_no, info in activity.items():
        for app, count in info["apps"].items():
            if count >= APP_USAGE_THRESHOLD:
                anomalies.insert_one({
                    "roll_no": roll_no,
                    "client_ip": info["client_ip"],
                    "type": "EXCESSIVE_APP_USAGE",
                    "app_name": app if app != "Unknown" else "High Usage Traffic",
                    "count": count,
                    "window_minutes": WINDOW_MINUTES,
                    "window_start": WINDOW_START,
                    "severity": "medium",
                    "detected_by": "rule",
                    "auto_ban": False,
                    "timestamp": datetime.now(UTC)
                })

# =========================
# Rule 2: Category Abuse
# =========================
def rule_category_abuse(activity):
    for roll_no, info in activity.items():
        total = info["total"]
        video = info["categories"].get("video", 0)
        social = info["categories"].get("social", 0)

        ratio = (video + social) / max(total, 1)

        if ratio >= CATEGORY_ABUSE_RATIO:
            anomalies.insert_one({
                "roll_no": roll_no,
                "client_ip": info["client_ip"],
                "type": "CATEGORY_ABUSE",
                "app_name": "Video/Social Traffic",
                "ratio": round(ratio, 2),
                "window_minutes": WINDOW_MINUTES,
                "window_start": WINDOW_START,
                "severity": "medium",
                "detected_by": "rule",
                "auto_ban": False,
                "timestamp": datetime.now(UTC)
            })

# =========================
# Rule 3: Traffic Spike
# =========================
def rule_traffic_spike():
    now = datetime.now(UTC)
    curr_start = now - timedelta(minutes=WINDOW_MINUTES)
    prev_start = now - timedelta(minutes=WINDOW_MINUTES * 2)

    current = {
        r["_id"]: r["count"]
        for r in detections.aggregate([
            {
                "$match": {
                    "timestamp": {"$gte": curr_start},
                    "roll_no": {"$exists": True},
                    "client_ip": {"$ne": ""},
                    "category": {"$ne": "general"}
                }
            },
            {"$group": {"_id": "$roll_no", "count": {"$sum": 1}}}
        ])
    }

    previous = {
        r["_id"]: r["count"]
        for r in detections.aggregate([
            {
                "$match": {
                    "timestamp": {"$gte": prev_start, "$lt": curr_start},
                    "roll_no": {"$exists": True},
                    "client_ip": {"$ne": ""},
                    "category": {"$ne": "general"}
                }
            },
            {"$group": {"_id": "$roll_no", "count": {"$sum": 1}}}
        ])
    }

    for roll_no, curr_count in current.items():
        prev_count = previous.get(roll_no, 1)
        if curr_count > prev_count * SPIKE_MULTIPLIER:
            anomalies.insert_one({
                "roll_no": roll_no,
                "type": "TRAFFIC_SPIKE",
                "current_count": curr_count,
                "previous_count": prev_count,
                "window_start": WINDOW_START,
                "severity": "high",
                "detected_by": "rule",
                "auto_ban": False,
                "timestamp": now
            })

# =========================
# Auto-Ban Logic
# =========================
def update_auto_ban():
    since = datetime.now(UTC) - timedelta(minutes=AUTO_BAN_WINDOW_MINUTES)

    pipeline = [
        {"$match": {"timestamp": {"$gte": since}}},
        {"$group": {"_id": "$roll_no", "count": {"$sum": 1}}},
        {"$match": {"count": {"$gte": AUTO_BAN_LIMIT}}}
    ]

    for r in anomalies.aggregate(pipeline):
        anomalies.update_many(
            {"roll_no": r["_id"], "auto_ban": False},
            {"$set": {"auto_ban": True}}
        )

# =========================
# Main Runner
# =========================
def run_anomaly_detection():
    activity = aggregate_recent_activity()
    rule_excessive_app_usage(activity)
    rule_category_abuse(activity)
    rule_traffic_spike()
    update_auto_ban()
    print("✅ Anomaly detection cycle completed")

if __name__ == "__main__":
    run_anomaly_detection()
