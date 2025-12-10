from pymongo import MongoClient
from datetime import datetime

# Adjust URI if your MongoDB runs elsewhere or uses auth
MONGO_URI = "mongodb://localhost:27017"
DB_NAME = "studentapp"
COLLECTION = "users"

client = MongoClient(MONGO_URI)
db = client[DB_NAME]
users = db[COLLECTION]

defaults = {
    "data": 0.0,         # total data used (GB)
    "ip": "",            # last seen IP
    "blocked": False,    # blocked status
    "activity": "",      # current activity or notes
    "device": "",        # device description
    "last_seen": None    # timestamp (null if unknown)
}

print(f"Checking collection: {DB_NAME}.{COLLECTION}")
for field, default in defaults.items():
    res = users.update_many({field: {"$exists": False}}, {"$set": {field: default}})
    print(f" - {field}: set default on {res.modified_count} documents")

# Optional: show a sample document after changes
sample = users.find_one()
print("\nSample document (trimmed):")
if sample:
    for k in ["_id"] + list(defaults.keys()) + ["name", "email", "roll_no"]:
        if k in sample:
            print(f"  {k}: {sample[k]}")
else:
    print("  (no documents found)")