# auto_monitor.py
import time
from capture import start_capture_stream
from analyze_activity import analyze_packet
from save_detections_batch import save_detections_batch
from session_lookup import get_all_active_ips
from anomaly_detector import run_anomaly_detection

# 🔁 Real-time ML + blocking
from realtime_ml import ml_anomaly_check
from decision_engine import should_block
from block_user import block_user

CAPTURE_INTERVAL = 60  # seconds
INTERFACE = "Wi-Fi"


def realtime_decision(roll_no, rule_triggered):
    ml_flag = ml_anomaly_check(roll_no)

    if should_block(rule_triggered, ml_flag):
        block_user(
            roll_no,
            reason="Real-time anomaly detected (Rule + ML)"
        )
        print(f"🚫 User blocked in real-time: {roll_no}")


def main():
    print("🚀 Real-time Wi-Fi monitoring started")

    buffer = []
    last_flush = time.time()

    try:
        for packet in start_capture_stream(INTERFACE):

            active_ips = get_all_active_ips()
            if packet["client_ip"] not in active_ips:
                continue

            detection = analyze_packet(packet)
            if detection:
                buffer.append(detection)

            # ⏱ Flush every CAPTURE_INTERVAL seconds
            if time.time() - last_flush >= CAPTURE_INTERVAL:
                if buffer:
                    save_detections_batch(buffer)

                    # 🔍 Rule-based anomaly detection (batch)
                    run_anomaly_detection()

                    # 🔁 Real-time decision per user
                    for d in buffer:
                        roll_no = d.get("roll_no")
                        if not roll_no:
                            continue

                        # Simple rule trigger signal
                        rule_triggered = d.get("score", 1) > 1
                        realtime_decision(roll_no, rule_triggered)

                    buffer.clear()

                last_flush = time.time()

    except KeyboardInterrupt:
        print("🛑 Monitoring stopped by user")
    except Exception as e:
        print(f"⚠️ Runtime error: {e}")


if __name__ == "__main__":
    main()
