# analyze_activity.py
import pandas as pd
from datetime import datetime
from model import classify
from domain_map import get_app_name
from save_detections_batch import save_detections_batch

def analyze_rows(rows):
    detections = []

    for r in rows:
        domain = r.get("domain", "").lower()
        if not domain:
            continue

        app_name = get_app_name(domain)
        category = classify(domain)

        detections.append({
            "roll_no": r.get("client_ip"),     # using IP as roll_no for now
            "client_ip": r.get("client_ip"),
            "domain": domain,
            "app_name": app_name,
            "category": category,
            "timestamp": r.get("timestamp", datetime.utcnow()),
            "reason": f"{app_name} activity",
            "score": 1,
            "details": f"domain={domain}"
        })

    save_detections_batch(detections)
