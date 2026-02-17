#!/usr/bin/env python3
"""
Database Setup Script for WiFi Management System
This script creates the MongoDB database and all required collections
"""

from pymongo import MongoClient
from werkzeug.security import generate_password_hash
from datetime import datetime

# Connect to MongoDB
print("🔌 Connecting to MongoDB...")
client = MongoClient("mongodb://localhost:27017/")
db = client["studentapp"]

# Create collections
print("📦 Creating collections...")
collections = [
    "users",
    "admins", 
    "active_sessions",
    "blocked_users",
    "web_filter",
    "logs"
]

for collection_name in collections:
    if collection_name not in db.list_collection_names():
        db.create_collection(collection_name)
        print(f"  ✅ Created collection: {collection_name}")
    else:
        print(f"  ⏭️  Collection already exists: {collection_name}")

# Create default admin user
print("\n👤 Creating default admin user...")
admins_collection = db["admins"]

# Check if admin already exists
if admins_collection.find_one({"username": "admin"}):
    print("  ⚠️  Admin user already exists. Skipping...")
else:
    admin_password = "Admin@123"
    hashed_password = generate_password_hash(admin_password)
    
    admin_user = {
        "username": "admin",
        "password": hashed_password,
        "created_at": datetime.now()
    }
    
    admins_collection.insert_one(admin_user)
    print(f"  ✅ Admin user created!")
    print(f"     Username: admin")
    print(f"     Password: {admin_password}")
    print(f"     🔐 Password is hashed in database")

# Create some sample web filter categories
print("\n🌐 Setting up web filter categories...")
web_filter_collection = db["web_filter"]

if web_filter_collection.count_documents({}) == 0:
    categories = [
        {"category": "social_media", "active": True, "domains": ["facebook.com", "twitter.com", "instagram.com"]},
        {"category": "gaming", "active": False, "domains": ["steam.com", "epicgames.com"]},
        {"category": "streaming", "active": False, "domains": ["youtube.com", "netflix.com", "twitch.tv"]},
        {"category": "adult_content", "active": True, "domains": []}
    ]
    
    web_filter_collection.insert_many(categories)
    print("  ✅ Web filter categories created")
else:
    print("  ⏭️  Web filter categories already exist")

# Verify database creation
print("\n✨ Database Setup Complete!")
print(f"\n📊 Database: studentapp")
print(f"📋 Collections created: {len(collections)}")
print(f"\n🔍 Verification:")
for collection_name in db.list_collection_names():
    count = db[collection_name].count_documents({})
    print(f"  • {collection_name}: {count} documents")

print("\n🚀 You can now run: python3 app.py")
print("🌐 Access the app at: http://localhost:5000")
