# save_detections_batch.py
from datetime import datetime
from db_client import get_collection

def save_detections_batch(items):
    if not items:
        return

    try:
        col = get_collection()
        # Don't check collection truthiness - MongoDB collections don't support it
        # get_collection() will either return the collection or None
        
        docs = []
        for i in items:
            try:
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
            except Exception as e:
                print(f"⚠️ Error processing detection item: {e}")
                continue

        if docs:
            try:
                col.insert_many(docs)
                # Reduced logging - only log count, not every save
            except Exception as e:
                print(f"❌ Error inserting to database: {e}")
        else:
            print("⚠️ No valid detections to save")

    except Exception as e:
        print(f"❌ Error saving detections batch: {e}")
