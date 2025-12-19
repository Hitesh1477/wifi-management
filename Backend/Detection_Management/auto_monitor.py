# auto_monitor.py
from capture import start_capture_stream
from analyze_activity import analyze_rows
import signal
import sys
import time
from datetime import datetime, timedelta

# Graceful shutdown handler
def signal_handler(sig, frame):
    print("\n⚠️ Monitoring stopped by user")
    sys.exit(0)

def auto_monitor(interface="Wi-Fi", interval_minutes=1):
    signal.signal(signal.SIGINT, signal_handler)
    print("🚀 Real-time monitoring started...")
    print(f"💾 Saving detections every {interval_minutes} minute(s)")
    print("Press Ctrl+C to stop\n")

    buffer = []
    next_save_time = datetime.now() + timedelta(minutes=interval_minutes)

    try:
        for row in start_capture_stream(interface):
            buffer.append(row)

            # ✅ Check if it's time to save (every 1 minute)
            if datetime.now() >= next_save_time:
                if buffer:
                    print(f"⏰ {interval_minutes} minute(s) elapsed. Saving {len(buffer)} detections...")
                    analyze_rows(buffer)
                    buffer.clear()
                else:
                    print(f"⏰ {interval_minutes} minute(s) elapsed. No activity detected.")
                
                # Set next save time
                next_save_time = datetime.now() + timedelta(minutes=interval_minutes)

    except KeyboardInterrupt:
        print("\n⚠️ Monitoring stopped by user")
        if buffer:
            print("Saving remaining buffer...")
            analyze_rows(buffer)
    except Exception as e:
        print(f"❌ Error in auto_monitor: {e}")
        if buffer:
            print("Attempting to save buffered data...")
            analyze_rows(buffer)
        sys.exit(1)

if __name__ == "__main__":
    auto_monitor("Wi-Fi")
