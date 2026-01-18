# check_sessions.py - Debug script to view active sessions
from pymongo import MongoClient

client = MongoClient("mongodb://localhost:27017/")
db = client["studentapp"]

print("=== Active Sessions ===")
for session in db["active_sessions"].find():
    print(f"  roll_no: {session.get('roll_no')}")
    print(f"  client_ip: {session.get('client_ip')}")
    print(f"  status: {session.get('status')}")
    print("-" * 30)

print("\n=== Sample Captured IPs (from detections if any) ===")
for det in db["detections"].find().limit(5):
    print(f"  roll_no: {det.get('roll_no')}, client_ip: {det.get('client_ip')}")
