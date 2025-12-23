# test_api.py - Test the admin clients API
from pymongo import MongoClient

client = MongoClient("mongodb://localhost:27017/")
db = client["studentapp"]

# Test the query directly
users = list(db['users'].find({'role': {'$ne': 'admin'}}, {'password': 0}))
print(f"Found {len(users)} users with role != admin:")
for u in users:
    print(f"  - roll_no: {u.get('roll_no')}, role: {u.get('role')}")

# Also check all users
print("\nAll users in database:")
all_users = list(db['users'].find({}, {'password': 0}))
for u in all_users:
    print(f"  - roll_no: {u.get('roll_no')}, role: {u.get('role')}")
