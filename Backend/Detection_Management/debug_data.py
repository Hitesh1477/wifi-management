# Debug script to check actual data
from pymongo import MongoClient
from datetime import datetime, timedelta, UTC

client = MongoClient("mongodb://localhost:27017/")
db = client["studentapp"]

since = datetime.now(UTC) - timedelta(minutes=60)

pipeline = [
    {
        "$match": {
            "timestamp": {"$gte": since},
            "roll_no": {"$exists": True},
            "category": {"$ne": "general"}
        }
    },
    {
        "$group": {
            "_id": "$roll_no",
            "total": {"$sum": 1},
            "video": {"$sum": {"$cond": [{"$eq": ["$category", "video"]}, 1, 0]}},
            "social": {"$sum": {"$cond": [{"$eq": ["$category", "social"]}, 1, 0]}},
            "messaging": {"$sum": {"$cond": [{"$eq": ["$category", "messaging"]}, 1, 0]}}
        }
    }
]

data = list(db["detections"].aggregate(pipeline))

print("=" * 50)
print("User Activity Data (last 60 minutes)")
print("=" * 50)

for d in data:
    roll_no = d["_id"]
    total = d["total"]
    video = d["video"]
    social = d["social"]
    messaging = d["messaging"]
    
    video_ratio = video / total if total > 0 else 0
    social_ratio = social / total if total > 0 else 0
    combined_ratio = (video + social) / total if total > 0 else 0
    
    print(f"\nRoll No: {roll_no}")
    print(f"  Total requests: {total}")
    print(f"  Video: {video} ({video_ratio:.1%})")
    print(f"  Social: {social} ({social_ratio:.1%})")
    print(f"  Messaging: {messaging}")
    print(f"  Entertainment ratio: {combined_ratio:.1%}")
    print()
    print("  Anomaly thresholds:")
    print(f"    - High activity (>10): {'❌ YES' if total >= 10 else '✅ No'} ({total})")
    print(f"    - Video abuse (>40%): {'❌ YES' if video_ratio >= 0.4 else '✅ No'} ({video_ratio:.1%})")
    print(f"    - Social abuse (>40%): {'❌ YES' if social_ratio >= 0.4 else '✅ No'} ({social_ratio:.1%})")
    print(f"    - Combined abuse (>50%): {'❌ YES' if combined_ratio >= 0.5 else '✅ No'} ({combined_ratio:.1%})")
