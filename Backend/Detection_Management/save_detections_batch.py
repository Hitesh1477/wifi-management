# save_detections_batch.py
from datetime import datetime
from db_client import get_collection

def save_detections_batch(items):
    if not items:
        return

    col = get_collection()

    docs = []
    for i in items:
        docs.append({
            "roll_no": str(i["roll_no"]),
            "client_ip": i.get("client_ip"),
            "domain": i.get("domain"),
            "app_name": i.get("app_name", "Unknown"),
            "category": i.get("category", "general"),
            "timestamp": i.get("timestamp") or datetime.utcnow(),
            "reason": f"{i.get('app_name', 'Unknown')} activity",
            "score": float(i.get("score", 1)),
            "details": i.get("details", "")
        })

    col.insert_many(docs)
