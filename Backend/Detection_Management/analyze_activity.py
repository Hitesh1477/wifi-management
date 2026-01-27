# analyze_activity.py
import pandas as pd
from datetime import datetime
from model import classify
from domain_map import get_app_name
from save_detections_batch import save_detections_batch
from session_lookup import get_roll_no_from_ip
from db_client import web_filter

def analyze_packet(packet):
    """
    Analyze a single packet and return a detection object.
    Returns None if the packet should be skipped (no domain, not logged in, etc.)
    """
    try:
        client_ip = packet.get("client_ip")
        domain = packet.get("domain", "").lower()
        
        if not domain or not client_ip:
            return None
        
        # Lookup actual roll_no from IP address via active sessions
        roll_no = get_roll_no_from_ip(client_ip)
        
        # Skip if user is not logged in (no active session)
        if roll_no is None:
            return None
        
        app_name = get_app_name(domain)
        category = classify(domain)
        
        return {
            "roll_no": roll_no,
            "client_ip": client_ip,
            "domain": domain,
            "app_name": app_name,
            "category": category,
            "timestamp": packet.get("timestamp", datetime.utcnow()),
            "reason": f"{app_name} activity",
            "score": 1,
            "details": f"domain={domain}"
        }
    except Exception as e:
        print(f"⚠️ Error analyzing packet: {e}")
        return None

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
                
                # ✅ Skip if user is not logged in (no active session)
                if roll_no is None:
                    continue  # User not logged in, don't log detection

                # ✅ Create unique key to avoid duplicate entries in same batch
                activity_key = (roll_no, domain)
                if activity_key in seen_activities:
                    continue  # Skip duplicate
                seen_activities.add(activity_key)

                app_name = get_app_name(domain)
                category = classify(domain)

                # ✅ Check for blocking
                is_blocked = False
                block_reason = None
                
                try:
                    config = web_filter.find_one({"type": "config"})
                    if config:
                        # 1. Check Manual Blocks
                        if any(b in domain for b in config.get("manual_blocks", [])):
                            is_blocked = True
                            block_reason = "Manually Blocked Site"

                        # 2. Check Categories
                        cats = config.get("categories", {})
                        
                        # Map model categories to config categories
                        cat_map = {
                            "video": "Streaming",
                            "social": "Social Media",
                            "gaming": "Gaming",
                            "messaging": "Messaging"
                        }
                        
                        config_cat = cat_map.get(category)
                        if config_cat and cats.get(config_cat, {}).get("active"):
                            is_blocked = True
                            block_reason = f"Blocked Category: {config_cat}"
                except Exception as e:
                    print(f"⚠️ Error checking web filter: {e}")

                final_reason = f"{app_name} activity"
                score = 1
                if is_blocked:
                    final_reason = f"BLOCKED: {block_reason} ({app_name})"
                    score = 5 # Higher score for violations

                detections.append({
                    "roll_no": roll_no,  # ✅ Uses actual student roll number
                    "client_ip": client_ip,
                    "domain": domain,
                    "app_name": app_name,
                    "category": category,
                    "timestamp": r.get("timestamp", datetime.utcnow()),
                    "reason": final_reason,
                    "score": score,
                    "details": f"domain={domain}"
                })
            except Exception as e:
                print(f"⚠️ Error analyzing row: {e}")
                continue

        if detections:
            save_detections_batch(detections)
            print(f"✅ Processed {len(rows)} packets, saved {len(detections)} detections for logged-in users")
        else:
            print("ℹ️ No detections for logged-in users in this batch")

    except Exception as e:
        print(f"❌ Error in analyze_rows: {e}")
