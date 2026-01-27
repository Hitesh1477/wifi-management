from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
import sys

try:
    client = MongoClient("mongodb://localhost:27017/", serverSelectionTimeoutMS=5000)
    # Test connection
    client.admin.command('ping')
    db = client["studentapp"]
    detections = db["detections"]
    web_filter = db["web_filter"]
    print("✅ MongoDB connection established")
except (ConnectionFailure, ServerSelectionTimeoutError) as e:
    print(f"❌ MongoDB connection failed: {e}")
    print("Please ensure MongoDB is running on localhost:27017")
    sys.exit(1)
except Exception as e:
    print(f"❌ Unexpected database error: {e}")
    sys.exit(1)

def get_collection():
    try:
        return detections
    except Exception as e:
        print(f"❌ Error getting collection: {e}")
        return None

def insert_detection(doc):
    try:
        detections.insert_one(doc)
        return True
    except Exception as e:
        print(f"❌ Error inserting detection: {e}")
        return False
