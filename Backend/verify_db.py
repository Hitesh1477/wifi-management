# verify_db.py - Check MongoDB collections
from pymongo import MongoClient

client = MongoClient("mongodb://localhost:27017/")
db = client["studentapp"]

print("=" * 60)
print("MongoDB Collections in 'studentapp':")
print("=" * 60)

for coll_name in db.list_collection_names():
    count = db[coll_name].count_documents({})
    print(f"  📁 {coll_name}: {count} documents")

print("\n" + "=" * 60)
print("Anomalies Collection:")
print("=" * 60)
anomalies = list(db['anomalies'].find().limit(5))
if anomalies:
    for doc in anomalies:
        print(f"  - {doc}")
else:
    print("  (No anomalies found)")

print("\n" + "=" * 60)
print("Detections Collection (last 5):")
print("=" * 60)
detections = list(db['detections'].find().sort([('timestamp', -1)]).limit(5))
if detections:
    for doc in detections:
        print(f"  ▸ Roll: {doc.get('roll_no')}, Domain: {doc.get('domain')}, Category: {doc.get('category')}")
else:
    print("  (No detections found)")

print("\n" + "=" * 60)
print("Active Sessions:")
print("=" * 60)
sessions = list(db['active_sessions'].find())
if sessions:
    for s in sessions:
        print(f"  👤 {s.get('roll_no')} -> IP: {s.get('client_ip')}")
else:
    print("  (No active sessions)")
