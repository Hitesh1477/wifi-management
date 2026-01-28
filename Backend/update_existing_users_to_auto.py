"""
Update all existing users to AUTO bandwidth mode
"""
from pymongo import MongoClient

client = MongoClient("mongodb://localhost:27017/")
db = client["studentapp"]
users = db["users"]

print("🔄 Updating all existing users to AUTO bandwidth mode...")
print("=" * 60)

# Update all student users that don't have bandwidth_limit set to 'auto'
result = users.update_many(
    {
        "role": "student",
        "$or": [
            {"bandwidth_limit": {"$exists": False}},
            {"bandwidth_limit": None},
            {"bandwidth_limit": ""}
        ]
    },
    {
        "$set": {
            "bandwidth_limit": "auto"
        }
    }
)

print(f"✅ Updated {result.modified_count} users to AUTO bandwidth mode")

# Show current bandwidth distribution
print("\n📊 Current bandwidth distribution:")
pipeline = [
    {"$match": {"role": "student"}},
    {"$group": {
        "_id": "$bandwidth_limit",
        "count": {"$sum": 1}
    }},
    {"$sort": {"count": -1}}
]

distribution = list(users.aggregate(pipeline))
for item in distribution:
    mode = item["_id"] or "None/Empty"
    count = item["count"]
    print(f"   {mode}: {count} users")

print("\n✅ Migration complete!")
