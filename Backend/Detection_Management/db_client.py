# db_client.py
from pymongo import MongoClient

# Local MongoDB on default port
MONGO_URI = "mongodb://127.0.0.1:27017"

_client = MongoClient(MONGO_URI)
_db = _client["studentapp"]

def get_collection():
    return _db["detections"]
