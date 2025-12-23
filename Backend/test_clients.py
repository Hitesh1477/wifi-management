# test_clients.py - Test the clients API
from pymongo import MongoClient

client = MongoClient("mongodb://localhost:27017/")
db = client["studentapp"]

print("Collections:", db.list_collection_names())
print("Detections exists:", 'detections' in db.list_collection_names())

# Test the query
users_collection = db['users']
clients_cursor = users_collection.find({"role": {"$ne": "admin"}}, {"password": 0})
print("\nClients found:")
for c in clients_cursor:
    print(f"  - {c.get('roll_no')} (role: {c.get('role')})")

# Check if detections exist
if 'detections' in db.list_collection_names():
    detections_col = db['detections']
    count = detections_col.count_documents({})
    print(f"\nDetections count: {count}")
