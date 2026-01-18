import requests
import sys
from pymongo import MongoClient

def check_backend():
    print("⏳ Checking Backend API...")
    try:
        response = requests.get("http://127.0.0.1:5000/")
        if response.status_code == 200 or response.status_code == 404: # Flask default might be 404 if root not defined
            print("✅ Backend is responding (http://127.0.0.1:5000)")
            return True
        else:
            print(f"⚠️ Backend returned status: {response.status_code}")
            return True # Still technically running
    except requests.exceptions.ConnectionError:
        print("❌ Backend is NOT running on http://127.0.0.1:5000")
        return False

def check_db():
    print("⏳ Checking MongoDB...")
    try:
        client = MongoClient("mongodb://localhost:27017/", serverSelectionTimeoutMS=2000)
        client.admin.command('ping')
        print("✅ MongoDB is running and accessible")
        
        db = client["studentapp"]
        cols = db.list_collection_names()
        required = ["users", "admins", "web_filter", "blocked_users"]
        missing = [c for c in required if c not in cols]
        
        if missing:
            print(f"⚠️ Missing optional collections: {missing}")
        else:
            print("✅ All core collections present")
        return True
    except Exception as e:
        print(f"❌ MongoDB Error: {e}")
        return False

if __name__ == "__main__":
    print("="*40)
    print("🔍 SYSTEM HEALTH CHECK")
    print("="*40)
    
    db_ok = check_db()
    
    print("-" * 20)
    
    backend_ok = check_backend()
    
    print("="*40)
    if db_ok and backend_ok:
        print("🚀 System appears ready!")
    else:
        print("🛑 Issues found. Please fix before testing.")
