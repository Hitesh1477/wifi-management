from pymongo import MongoClient

client = MongoClient("mongodb://localhost:27017/")
db = client["studentapp"]
detections = db["detections"]

print("Recent BGMI-related domains for user 23203A0068:")
print("=" * 80)

recent = list(detections.find({"roll_no": "23203A0068"}).sort("timestamp", -1).limit(20))

for d in recent:
    domain = d.get("domain", "N/A")
    category = d.get("category", "N/A")
    app_name = d.get("app_name", "Unknown")
    print(f"{domain:50} -> {category:15} ({app_name})")
