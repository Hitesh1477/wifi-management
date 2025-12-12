from pymongo import MongoClient

client = MongoClient("mongodb://localhost:27017/")
db = client["studentapp"]
detections = db["detections"]

def insert_detection(doc):
    detections.insert_one(doc)
    return True
