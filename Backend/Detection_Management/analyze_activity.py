# analyze_activity.py
# analyze_activity.py
import pandas as pd
from datetime import datetime
from model import classify
from domain_map import get_app_name
from save_detections_batch import save_detections_batch
from session_lookup import get_roll_no_from_ip

def analyze_rows(rows):
    if not rows:
        return

    detections = []
    seen_activities = set()  # ✅ Track unique (roll_no, domain) pairs to avoid duplicates

    try:
        for r in rows:
            try:
                client_ip = r.get("client_ip")
                domain = r.get("domain", "").lower()
                if not domain or not client_ip:
                    continue

                # ✅ Lookup actual roll_no from IP address via active sessions
                roll_no = get_roll_no_from_ip(client_ip)

                # ✅ Create unique key to avoid duplicate entries in same batch
                activity_key = (roll_no, domain)
                if activity_key in seen_activities:
                    continue  # Skip duplicate
                seen_activities.add(activity_key)

                app_name = get_app_name(domain)
                category = classify(domain)

                detections.append({
                    "roll_no": roll_no,  # ✅ Now uses actual student roll number
                    "client_ip": client_ip,
                    "domain": domain,
                    "app_name": app_name,
                    "category": category,
                    "timestamp": r.get("timestamp", datetime.utcnow()),
                    "reason": f"{app_name} activity",
                    "score": 1,
                    "details": f"domain={domain}"
                })
            except Exception as e:
                print(f"⚠️ Error analyzing row: {e}")
                continue

        if detections:
            save_detections_batch(detections)
            print(f"✅ Processed {len(rows)} packets, saved {len(detections)} unique detections")
        else:
            print("⚠️ No valid detections to analyze")

    except Exception as e:
        print(f"❌ Error in analyze_rows: {e}")
