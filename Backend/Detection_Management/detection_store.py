# detection_store.py
from datetime import datetime
from db_client import get_collection

def _make_doc(roll_no, timestamp, reason, score, details=None):
    return {
        "roll_no": str(roll_no),
        "timestamp": timestamp if timestamp is not None else datetime.utcnow(),
        "reason": str(reason),
        "score": float(score),
        "details": details or ""
    }

def save_detections_batch(items):
    """
    items: list of dicts with keys:
      - roll_no
      - timestamp (datetime or None)
      - reason
      - score
      - details (optional)
    """
    if not items:
        return

    col = get_collection()
    docs = [
        _make_doc(
            i["roll_no"],
            i.get("timestamp"),
            i["reason"],
            i["score"],
            i.get("details")
        )
        for i in items
    ]
    col.insert_many(docs)
