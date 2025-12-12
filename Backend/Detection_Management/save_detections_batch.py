from db_client import detections
from datetime import datetime

def save_detection(row):
    ts = row.get("timestamp")
    try:
        ts = datetime.utcfromtimestamp(float(ts))
    except:
        ts = datetime.utcnow()

    doc = {
        "client_ip": row.get("client_ip"),
        "domain": row.get("domain", "").lower(),
        "app_name": row.get("app_name", "Unknown"),
        "category": row.get("category", "general"),
        "timestamp": ts
    }

    detections.insert_one(doc)
    print(f"✔ Stored -> {doc}")
