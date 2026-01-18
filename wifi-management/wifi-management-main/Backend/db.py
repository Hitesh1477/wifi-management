from pymongo import MongoClient

client = MongoClient("mongodb://localhost:27017/")
db = client["studentapp"]

# ✅ EXPORT COLLECTIONS
users_collection = db["users"]
admins_collection = db["admins"]
sessions_collection = db["active_sessions"]
blocked_users_collection = db["blocked_users"]
web_filter_collection = db["web_filter"]
