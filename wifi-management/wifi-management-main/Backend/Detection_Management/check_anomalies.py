# Quick check anomalies
from pymongo import MongoClient

client = MongoClient("mongodb://localhost:27017/")
db = client["studentapp"]

count = db['anomalies'].count_documents({})
print(f"✅ Total Anomalies: {count}")

if count > 0:
    print("\nLatest anomalies:")
    for a in db['anomalies'].find().sort('timestamp', -1).limit(5):
        roll = a.get('roll_no', 'N/A')
        atype = a.get('type', 'N/A')
        model = a.get('ml_model', 'rule-based')
        conf = a.get('confidence', 'N/A')
        severity = a.get('severity', 'N/A')
        reason = a.get('reason', 'No reason provided')
        features = a.get('features', {})
        
        print(f"\n  Roll No: {roll}")
        print(f"    Type: {atype}")
        print(f"    Model: {model}")
        print(f"    Confidence: {conf}")
        print(f"    Severity: {severity}")
        print(f"    📌 Reason: {reason}")
        if features:
            gaming = features.get('gaming_count', 0)
            social = features.get('social_count', 0)
            video = features.get('video_count', 0)
            print(f"    Features: total={features.get('total_requests')}, gaming={gaming}, social={social}, video={video}")

