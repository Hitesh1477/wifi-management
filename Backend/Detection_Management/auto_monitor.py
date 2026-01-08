# auto_monitor.py
import time
from collections import defaultdict

from capture import start_capture_stream
from analyze_activity import analyze_packet
from save_detections_batch import save_detections_batch
from session_lookup import get_all_active_ips
from anomaly_detector import run_anomaly_detection
from decision_engine import should_block
from block_user import block_user
from ml_random_forest import rf_anomaly_check

CAPTURE_INTERVAL = 60
INTERFACE = "Wi-Fi"

def build_features(detections):
    total = len(detections)
    if total == 0:
        return None

    counts = defaultdict(int)
    for d in detections:
        counts[d["category"]] += 1

    video = counts.get("video", 0)
    social = counts.get("social", 0)
    messaging = counts.get("messaging", 0)
    gaming = counts.get("gaming", 0)

    video_ratio = video / total
    social_ratio = social / total
    messaging_ratio = messaging / total
    gaming_ratio = gaming / total
    entertainment_ratio = (video + social + gaming) / total

    return [
        total,
        video,
        social,
        messaging,
        gaming,
        video_ratio,
        social_ratio,
        messaging_ratio,
        gaming_ratio,
        entertainment_ratio
    ]

def main():
    buffer = []
    last_flush = time.time()

    while True:
        try:
            active_ips = get_all_active_ips()
            for packet in start_capture_stream(INTERFACE):
                if packet["client_ip"] not in active_ips:
                    continue

                detection = analyze_packet(packet)
                if detection:
                    buffer.append(detection)

                if time.time() - last_flush >= CAPTURE_INTERVAL:
                    if buffer:
                        save_detections_batch(buffer)
                        run_anomaly_detection()

                        per_user = defaultdict(list)
                        for d in buffer:
                            roll_no = d.get("roll_no")
                            if roll_no:
                                per_user[roll_no].append(d)

                        for roll_no, user_data in per_user.items():
                            rule_flag = any(d.get("score", 1) > 1 for d in user_data)

                            features = build_features(user_data)
                            if not features:
                                continue

                            ml_flag, confidence = rf_anomaly_check(features)

                            if should_block(rule_flag, ml_flag):
                                block_user(
                                    roll_no,
                                    confidence,
                                    reason="Auto-ban triggered by Rule + Random Forest ML"
                                )

                        buffer.clear()
                    last_flush = time.time()

        except KeyboardInterrupt:
            break
        except Exception:
            time.sleep(5)

if __name__ == "__main__":
    main()
